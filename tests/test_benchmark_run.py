"""No paid calls: verify tool-free input and crash-safe complete-selection accounting."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage

from provenance.benchmark_run import INSTRUCTIONS, parse_output, run_prepared
from provenance.benchmarks import prepare
from provenance.controls import Budget
from provenance.langchain_model import OpenRouterModel
from provenance.transport import ProviderError


def prepared():
    tasks = [
        {
            "id": str(i),
            "dataset": "fineval",
            "subset": "CFA-Easy",
            "source_split": "test",
            "question": "Synthetic? A: yes B: no",
            "context": {},
            "reference": {"answer": "B", "metric": "choice_accuracy", "secret": "GOLD_SENTINEL"},
            "metadata": {},
        }
        for i in range(10)
    ]
    return prepare(
        tasks,
        source={
            "url": "https://example.org",
            "revision": "a" * 40,
            "sha256": "b" * 64,
            "license": "synthetic",
            "dataset": "fineval",
            "subset": "CFA-Easy",
            "source_split": "test",
        },
        count=3,
        seed=17,
        condition="model_only",
    )


def response(text='{"answer":"B"}'):
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
        step=step,
    )


class BenchmarkRunTests(unittest.TestCase):
    def test_model_sees_no_reference_and_all_outputs_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            seen = []

            def step(messages, timeout, budget):
                self.assertNotIn("GOLD_SENTINEL", str(messages))
                seen.append(messages)
                amount = budget.reserve(0.01)
                budget.settle(amount, 0.005)
                return response()

            ledger = run_prepared(
                prepared(), fake(step), Path(tmp) / "run", budget_usd=0.06, per_task_usd=0.02
            )
            self.assertEqual(len(seen), 3)
            self.assertAlmostEqual(ledger["accounted_cost_usd"], 0.015)
            score = json.loads((Path(tmp) / "run/score.json").read_text())
            self.assertEqual(score["passed_count"], 3)
            self.assertEqual(score["selected_count"], 3)

    def test_crash_retains_reservation_and_no_automatic_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"

            def crash(*args):
                state = json.loads((output / "submission.json").read_text())
                self.assertEqual(len(state["predictions"]), 3)
                self.assertEqual(state["predictions"][0]["status"], "pending")
                raise RuntimeError("simulated process death")

            with self.assertRaises(RuntimeError):
                run_prepared(prepared(), fake(crash), output, budget_usd=0.06, per_task_usd=0.02)
            state = json.loads((output / "submission.json").read_text())
            self.assertAlmostEqual(state["accounted_cost_usd"], 0.02)
            with self.assertRaises(FileExistsError):
                run_prepared(prepared(), fake(crash), output, budget_usd=0.06, per_task_usd=0.02)

    def test_uncertain_cost_stops_with_all_remaining_ids_visible(self):
        with tempfile.TemporaryDirectory() as tmp:

            def fail(messages, timeout, budget):
                budget.reserve(0.01)
                budget.uncertain = True
                raise ProviderError("uncertain request")

            ledger = run_prepared(
                prepared(), fake(fail), Path(tmp) / "run", budget_usd=0.06, per_task_usd=0.02
            )
            self.assertEqual(ledger["status"], "stopped_for_billing_review")
            self.assertEqual(
                [r["status"] for r in ledger["predictions"]], ["failed", "skipped", "skipped"]
            )
            self.assertAlmostEqual(ledger["accounted_cost_usd"], 0.01)
            score = json.loads((Path(tmp) / "run/score.json").read_text())
            self.assertEqual(score["selected_count"], 3)
            self.assertEqual(score["passed_count"], 0)

    def test_budget_exhaustion_keeps_unattempted_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:

            def step(messages, timeout, budget):
                budget.reserve(budget.limit)
                return response()

            ledger = run_prepared(
                prepared(), fake(step), Path(tmp) / "run", budget_usd=0.03, per_task_usd=0.03
            )
            self.assertEqual(ledger["status"], "aggregate_budget_exhausted")
            self.assertEqual(
                [r["status"] for r in ledger["predictions"]], ["completed", "skipped", "skipped"]
            )

    def test_malformed_or_conflicting_json_never_silently_extracts_answer(self):
        for text in (
            '{"answer":"A","answer":"B"}',
            '{"answer":NaN}',
            '{"answer":1e309}',
            '```json\n{"answer":"B"}\n```',
        ):
            self.assertEqual(parse_output(response(text), structured=True), (None, "invalid_json"))
        with self.assertRaises(ProviderError):
            parse_output(
                {"status": "completed", "output": [{"type": "function_call"}]}, structured=True
            )

    def test_empty_text_is_invalid_and_truncated_response_is_retained(self):
        for text in ("", "   "):
            self.assertEqual(parse_output(response(text), structured=False), (None, "empty_output"))
        chat = Mock()
        chat.bind.return_value.invoke.return_value = AIMessage(
            content="partial answer",
            usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            response_metadata={"finish_reason": "length"},
        )
        model = OpenRouterModel(
            "synthetic-key", "fake", 1, 1, chat=chat, instructions=INSTRUCTIONS, tool_schemas=[]
        )
        budget = Budget(1)
        with self.assertRaises(ProviderError):
            model.step([], 10, budget)
        self.assertAlmostEqual(budget.charged, 0.000015)
        self.assertFalse(budget.uncertain)
        self.assertEqual(model.last_response["content"], "partial answer")
        self.assertEqual(model.last_response["finish_reason"], "length")
        self.assertEqual(chat.bind.return_value.invoke.call_count, 1)

    def test_provider_unbinds_tools_and_uses_benchmark_instructions(self):
        chat = Mock()
        chat.bind.return_value.invoke.return_value = AIMessage(
            content='{"answer":"B"}',
            usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            response_metadata={"finish_reason": "stop"},
        )
        model = OpenRouterModel(
            "synthetic-key", "fake", 1, 1, chat=chat, instructions=INSTRUCTIONS, tool_schemas=[]
        )
        model.step([{"role": "user", "content": "Question"}], 10, Budget(1))
        chat.bind_tools.assert_not_called()
        messages = chat.bind.return_value.invoke.call_args.args[0]
        self.assertEqual(messages[0].content, INSTRUCTIONS)
        self.assertNotIn("tool_choice", chat.bind.call_args.kwargs)
        chat.bind.return_value.invoke.return_value = AIMessage(
            content="",
            additional_kwargs={
                "tool_calls": [
                    {"id": "bad", "function": {"name": "read_source", "arguments": "{}"}}
                ]
            },
            usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        )
        with self.assertRaises(ProviderError):
            model.step([], 10, Budget(1))


if __name__ == "__main__":
    unittest.main()
