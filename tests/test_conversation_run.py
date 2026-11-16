"""Fake-only checks for bounded ConvFinQA conversation execution."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from provenance.benchmark_run import INSTRUCTIONS
from provenance.benchmarks import prepare
from provenance.conversation_run import run_conversations
from provenance.table_conversation_adapters import adapt_convfinqa
from provenance.transport import ProviderError


def response(text):
    return {
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
    }


def fake(step):
    return SimpleNamespace(
        mode="synthetic_test",
        name="fake",
        instructions=INSTRUCTIONS,
        tool_schemas=[],
        input_rate=1,
        output_rate=1,
        max_output=100,
        last_response=None,
        step=step,
    )


def bundle(condition="agent_history", count=2):
    records = []
    for number in range(count):
        records.append(
            {
                "id": f"conversation-{number}",
                "filename": f"SYN/{number}/page_1.pdf",
                "pre_text": ["Permitted source context"],
                "post_text": [],
                "table": [["Metric", "Value"], ["Value", str(number + 2)]],
                "annotation": {
                    "dialogue_break": ["Value?", "Double it?", "Positive?"],
                    "turn_program": ["private-program-0", "private-program-1", "private-program-2"],
                    "exe_ans_list": [number + 2, (number + 2) * 2, "yes"],
                },
            }
        )
    tasks = adapt_convfinqa(records, source_split="dev")
    return prepare(
        tasks,
        source={
            "url": "https://example.org",
            "revision": "a" * 40,
            "sha256": "b" * 64,
            "license": "synthetic",
            "dataset": "convfinqa",
            "subset": "default",
            "source_split": "dev",
        },
        count=count,
        seed=17,
        condition=condition,
        development_groups=[f"SYN/{number}" for number in range(count)],
    )


class ConversationRunTests(unittest.TestCase):
    def run_case(self, data, step, **kwargs):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / "run"
        ledger = run_conversations(
            data,
            fake(step),
            output,
            budget_usd=kwargs.get("budget_usd", 1),
            per_task_usd=kwargs.get("per_task_usd", 0.2),
            per_turn_usd=kwargs.get("per_turn_usd", 0.05),
        )
        return ledger, output

    def test_future_gold_isolation_and_incorrect_actual_history(self):
        data = bundle(count=1)
        seen = []
        answers = iter([999, 4, "yes"])

        def step(messages, timeout, budget):
            payload = json.loads(messages[0]["content"])
            seen.append(payload)
            budget.settle(budget.reserve(0.01), 0.005)
            return response(json.dumps({"answer": next(answers)}))

        ledger, output = self.run_case(data, step)
        self.assertEqual(ledger["status"], "finished")
        self.assertEqual(seen[1]["history"], [{"question": "Value?", "answer": 999}])
        self.assertNotIn("Double it?", json.dumps(seen[0]))
        self.assertNotIn("Positive?", json.dumps(seen[0]))
        self.assertNotIn("private-program", json.dumps(seen))
        self.assertNotIn("exe_ans", json.dumps(seen))
        self.assertNotIn("reference", json.dumps(seen))
        self.assertEqual(seen[0], data["inputs"][0])
        self.assertEqual(json.loads((output / "score.json").read_text())["selected_count"], 1)

    def test_overflowing_numeric_string_cannot_become_history(self):
        callback = Mock(return_value=response(json.dumps({"answer": "1" + "0" * 400})))
        ledger, _ = self.run_case(bundle(count=1), callback)
        callback.assert_called_once()
        turns = ledger["predictions"][0]["output"]["turns"]
        self.assertEqual(turns[0]["status"], "invalid_output")
        self.assertEqual(
            [turn["status"] for turn in turns[1:]], ["skipped_after_invalid_history"] * 2
        )

    def test_reference_history_uses_gold_after_invalid_turn(self):
        data = bundle("reference_history", count=1)
        seen = []
        replies = iter(["not json", '{"answer":4}', '{"answer":"yes"}'])

        def step(messages, timeout, budget):
            seen.append(json.loads(messages[0]["content"]))
            budget.settle(budget.reserve(0.01), 0.005)
            return response(next(replies))

        ledger, _ = self.run_case(data, step)
        turns = ledger["predictions"][0]["output"]["turns"]
        self.assertEqual(
            [turn["status"] for turn in turns],
            ["invalid_output", "completed", "completed"],
        )
        self.assertEqual(seen[1]["history"], [{"question": "Value?", "answer": 2}])
        self.assertEqual(ledger["predictions"][0]["status"], "failed")

    def test_malformed_actual_history_stops_future_and_preserves_denominator(self):
        callback = Mock(return_value=response('{"answer":true}'))
        ledger, output = self.run_case(bundle(count=1), callback)
        callback.assert_called_once()
        turns = ledger["predictions"][0]["output"]["turns"]
        self.assertEqual(turns[0]["status"], "invalid_output")
        self.assertEqual(
            [turn["status"] for turn in turns[1:]],
            ["skipped_after_invalid_history"] * 2,
        )
        score = json.loads((output / "score.json").read_text())
        self.assertEqual(score["conversation_metrics"]["turn_count"], 3)
        self.assertEqual(score["conversation_metrics"]["turn_passed_count"], 0)

    def test_pending_reservation_survives_crash_and_output_reuse_is_blocked(self):
        data = bundle(count=1)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / "run"

        def crash(*args):
            state = json.loads((output / "submission.json").read_text())
            self.assertEqual(state["predictions"][0]["output"]["turns"][0]["status"], "pending")
            self.assertNotIn("Double it?", json.dumps(state))
            self.assertNotIn("private-program", json.dumps(state))
            raise RuntimeError("simulated crash")

        with self.assertRaisesRegex(RuntimeError, "simulated crash"):
            run_conversations(data, fake(crash), output, budget_usd=1, per_task_usd=0.2)
        state = json.loads((output / "submission.json").read_text())
        self.assertEqual(state["accounted_cost_usd"], 0.02)
        with self.assertRaises(FileExistsError):
            run_conversations(data, fake(crash), output, budget_usd=1, per_task_usd=0.2)

    def test_uncertain_billing_stops_all_conversations(self):
        def fail(messages, timeout, budget):
            budget.reserve(0.01)
            budget.uncertain = True
            raise ProviderError("uncertain request")

        ledger, _ = self.run_case(bundle(), fail)
        self.assertEqual(ledger["status"], "stopped_for_billing_review")
        self.assertEqual(ledger["accounted_cost_usd"], 0.05)
        self.assertEqual(ledger["predictions"][1]["status"], "skipped")
        self.assertTrue(
            all(turn["status"] == "skipped" for turn in ledger["predictions"][1]["output"]["turns"])
        )

    def test_conversation_and_global_caps(self):
        def spend_all(messages, timeout, budget):
            budget.reserve(budget.limit)
            return response('{"answer":1}')

        conversation_limited, _ = self.run_case(
            bundle(), spend_all, per_task_usd=0.06, per_turn_usd=0.05
        )
        self.assertEqual(
            [row["status"] for row in conversation_limited["predictions"]],
            ["conversation_budget_exhausted", "conversation_budget_exhausted"],
        )
        self.assertAlmostEqual(conversation_limited["accounted_cost_usd"], 0.12)

        global_limited, _ = self.run_case(
            bundle(), spend_all, budget_usd=0.06, per_task_usd=0.2, per_turn_usd=0.05
        )
        self.assertEqual(global_limited["status"], "aggregate_budget_exhausted")
        self.assertEqual(global_limited["predictions"][1]["status"], "skipped")
        self.assertAlmostEqual(global_limited["accounted_cost_usd"], 0.06)

    def test_known_charge_and_truncated_diagnostic_are_retained(self):
        model = fake(None)

        def truncated(messages, timeout, budget):
            budget.settle(budget.reserve(0.01), 0.004)
            model.last_response = {
                "content": "partial answer",
                "finish_reason": "length",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "private": "drop me",
            }
            raise ProviderError("Model response did not complete: length")

        model.step = truncated
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        ledger = run_conversations(
            bundle("reference_history", count=1),
            model,
            Path(temporary.name) / "run",
            budget_usd=1,
            per_task_usd=0.2,
        )
        first = ledger["predictions"][0]["output"]["turns"][0]
        self.assertEqual(first["accounted_cost_usd"], 0.004)
        self.assertEqual(first["rejected_provider_response"]["content"], "partial answer")
        self.assertNotIn("private", first["rejected_provider_response"])
        self.assertEqual(len(ledger["predictions"][0]["output"]["turns"]), 3)


if __name__ == "__main__":
    unittest.main()
