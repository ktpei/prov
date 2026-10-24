import copy
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from provenance.agent import Limits, Trace, run
from provenance.controls import Budget, DeadlineReached, LimitReached, deadline
from provenance.evaluation import grade, load_tasks
from provenance.model import OpenAIModel, ReplayModel
from provenance.sources import Sources
from provenance.transport import ProviderError


def call(name="search", arguments='{"query":"Acme"}', call_id="c1"):
    return {
        "status": "completed",
        "output": [
            {"type": "function_call", "name": name, "arguments": arguments, "call_id": call_id}
        ],
    }


def final(value=120, quote="Revenue FY2024: 120 USD million.", locator="L1"):
    answer = {
        "answerable": True,
        "answer": "Revenue was 120 USD million.",
        "claims": [
            {
                "key": "revenue",
                "value": value,
                "unit": "USD million",
                "period": "FY2024",
                "citations": [{"source_id": "acme", "locator": locator, "quote": quote}],
            }
        ],
    }
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": json.dumps(answer)}],
            }
        ],
    }


def read():
    return call("read_source", '{"source_id":"acme","start_line":1,"end_line":2}')


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        content = "Revenue FY2024: 120 USD million.\nRevenue FY2023: 100 USD million.\n"
        (self.root / "acme.txt").write_text(content)
        self.manifest = {
            "version": "1",
            "sources": [
                {
                    "id": "acme",
                    "title": "Acme annual results",
                    "company": "Acme",
                    "ticker": "ACME",
                    "url": "https://example.com/results",
                    "published": "2025-01-01",
                    "text_file": "acme.txt",
                    "sha256": hashlib.sha256(content.encode()).hexdigest(),
                }
            ],
        }
        (self.root / "sources.json").write_text(json.dumps(self.manifest))
        self.sources = Sources(self.root)

    def execute(self, responses, **limits):
        return run("Acme FY2024 revenue?", ReplayModel(responses), self.sources, Limits(**limits))

    def test_model_drives_tools_and_cited_answer(self):
        report = self.execute([call(), read(), final()])
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["metrics"]["tool_calls"], 2)
        self.assertEqual(report["metrics"]["accounted_cost_usd"], 0)
        self.assertEqual(report["mode"], "offline_replay")
        requests = [e for e in report["events"] if e["event"] == "model_request"]
        self.assertEqual(requests[-1]["input"][-1]["type"], "function_call_output")

    def test_unknown_tool_is_error_not_execution(self):
        report = self.execute([call("write_file", '{"path":"danger"}'), read(), final()])
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["metrics"]["tool_errors"], 1)
        self.assertFalse((self.root / "danger").exists())

    def test_malformed_arguments_can_be_recovered(self):
        report = self.execute([call(arguments="not json"), read(), final()])
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["metrics"]["tool_errors"], 1)

    def test_tool_limit_applies_inside_multi_call_response(self):
        response = call()
        response["output"].extend([read()["output"][0], call(call_id="c3")["output"][0]])
        report = self.execute([response], max_tool_calls=2)
        self.assertEqual(report["stop_reason"], "tool_call_limit")
        self.assertEqual(report["metrics"]["tool_calls"], 2)

    def test_model_call_limit(self):
        report = self.execute([call(), call()], max_model_calls=1)
        self.assertEqual(report["stop_reason"], "model_call_limit")

    def test_unread_citation_rejected(self):
        report = self.execute([final()])
        self.assertEqual(report["status"], "failed")
        self.assertIn("unread", report["stop_reason"])

    def test_huge_citation_span_rejected_without_allocation(self):
        report = self.execute([read(), final(locator="L1-L1000000000")])
        self.assertEqual(report["status"], "failed")
        self.assertIn("exceeds", report["stop_reason"])

    def test_reusing_sources_does_not_reuse_read_evidence(self):
        self.assertEqual(self.execute([read(), final()])["status"], "completed")
        self.assertEqual(self.execute([final()])["status"], "failed")

    def test_run_budget_overrides_stale_sources_budget(self):
        class Spender:
            name, mode = "spender", "test"

            def step(self, messages, timeout, budget):
                budget.reserve(0.25)
                return final()

        self.sources.budget = Budget(10)
        report = run("test", Spender(), self.sources, Limits(budget_usd=0.01))
        self.assertEqual(report["stop_reason"], "spend_limit")
        self.assertEqual(report["metrics"]["accounted_cost_usd"], 0)

    def test_invented_quote_rejected(self):
        report = self.execute([read(), final(quote="Revenue: 900")])
        self.assertEqual(report["status"], "failed")
        self.assertIn("absent", report["stop_reason"])

    def test_wrong_number_needs_semantic_grading(self):
        # The runtime verifies evidence presence, not whether a claim follows from it.
        report = self.execute([read(), final(value=999)])
        self.assertEqual(report["status"], "completed")
        self.assertIn("semantic accuracy", report["validation"])

    def test_nonfinite_value_rejected(self):
        report = self.execute([read(), final(value=float("nan"))])
        self.assertEqual(report["status"], "failed")

    def test_incomplete_response_rejected(self):
        report = self.execute([{"status": "incomplete", "output": []}])
        self.assertEqual(report["status"], "failed")

    def test_timeout_interrupts_blocking_provider(self):
        class SlowModel:
            name, mode = "slow", "test"

            def step(self, messages, timeout, budget):
                time.sleep(2)

        report = run("test", SlowModel(), self.sources, Limits(timeout_seconds=0.03))
        self.assertEqual(report["stop_reason"], "wall_clock_limit")
        self.assertLess(report["metrics"]["latency_seconds"], 1)

    def test_connection_reset_produces_final_failure_trace(self):
        model = OpenAIModel("fake", "example-model", 1, 2)
        with patch("urllib.request.OpenerDirector.open") as opened:
            opened.return_value.__enter__.return_value.read.side_effect = ConnectionResetError()
            report = run("test", model, self.sources)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["events"][-1]["event"], "run_finished")
        self.assertTrue(report["metrics"]["cost_uncertain"])

    def test_log_directory_is_explicit_and_trace_complete(self):
        trace = Trace(self.root / "logs")
        report = run("test", ReplayModel([read(), final()]), self.sources, trace=trace)
        self.assertEqual(json.loads((trace.directory / "result.json").read_text()), report)
        events = [
            json.loads(line) for line in (trace.directory / "trace.jsonl").read_text().splitlines()
        ]
        self.assertEqual(events[0]["event"], "run_started")
        self.assertEqual(events[-1]["event"], "run_finished")

    def test_tampered_corpus_rejected(self):
        (self.root / "acme.txt").write_text("Revenue: 999")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            Sources(self.root)

    def test_read_range_and_tool_argument_validation(self):
        for args in (
            [],
            {"source_id": "acme", "start_line": True, "end_line": 2},
            {"source_id": "acme", "start_line": 1, "end_line": 500},
        ):
            self.assertIn("error", self.sources.call("read_source", args, 1))

    def test_exa_search_and_contents_shapes(self):
        requests = []

        def request(url, payload, headers, timeout):
            requests.append((url, payload))
            if url.endswith("search"):
                return {
                    "results": [{"url": "https://example.com/extra", "title": "Extra"}],
                    "costDollars": {"total": 0.001},
                }
            return {
                "results": [{"url": "https://example.com/extra", "text": "Revenue: 10"}],
                "costDollars": {"total": 0.001},
            }

        self.sources = Sources(
            self.root, exa_key="fake", exa_cap=0.01, budget=Budget(0.1), request=request
        )
        hits = self.sources.search("Acme", 1)["results"]
        source_id = next(hit["id"] for hit in hits if hit["id"].startswith("web-"))
        result = self.sources.read(source_id, 1, 20, 1)
        self.assertEqual(result["lines"][0]["text"], "Revenue: 10")
        self.assertEqual(requests[1][1]["urls"], ["https://example.com/extra"])
        self.assertAlmostEqual(self.sources.budget.charged, 0.002)

    def test_exa_missing_cost_retains_reservation(self):
        source = Sources(
            self.root,
            exa_key="fake",
            exa_cap=0.01,
            budget=Budget(0.1),
            request=lambda *args: {"results": []},
        )
        source.search("Acme", 1)
        self.assertAlmostEqual(source.budget.charged, 0.01)
        self.assertTrue(source.budget.uncertain)


class BudgetAndProviderTests(unittest.TestCase):
    def test_invalid_limits(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                Limits(budget_usd=value)

    def test_request_blocked_before_spending(self):
        request = unittest.mock.Mock()
        model = OpenAIModel("fake-key", "example-model", 10, 30, request=request)
        with self.assertRaises(LimitReached):
            model.step([], 1, Budget(0.000001))
        request.assert_not_called()

    def test_usage_cost_and_fixed_endpoint(self):
        captured = []

        def request(url, payload, headers, timeout):
            captured.append((url, payload))
            return {
                "status": "completed",
                "output": [],
                "usage": {"input_tokens": 100, "output_tokens": 20},
            }

        model = OpenAIModel("secret", "example-model", 1, 2, request=request)
        budget = Budget(1)
        model.step([], 1, budget)
        self.assertAlmostEqual(budget.charged, 0.00014)
        self.assertFalse(captured[0][1]["store"])
        self.assertEqual(captured[0][0], "https://api.openai.com/v1/responses")

    def test_failure_reservation_not_refunded(self):
        def fail(*args):
            raise ProviderError("API HTTP 500")

        budget = Budget(1)
        model = OpenAIModel("secret", "example-model", 1, 2, request=fail)
        with self.assertRaises(ProviderError):
            model.step([], 1, budget)
        self.assertGreater(budget.charged, 0)
        self.assertTrue(budget.uncertain)

    def test_actual_above_reservation_stops(self):
        budget = Budget(1)
        reserved = budget.reserve(0.01)
        with self.assertRaisesRegex(LimitReached, "reservation_exceeded"):
            budget.settle(reserved, 0.02)
        self.assertAlmostEqual(budget.charged, 0.02)

    def test_missing_usage_stops_and_retains_reservation(self):
        budget = Budget(1)
        model = OpenAIModel("secret", "example-model", 1, 2, request=lambda *args: {})
        with self.assertRaises(ProviderError):
            model.step([], 1, budget)
        self.assertGreater(budget.charged, 0)

    def test_deadline_restores_signal(self):
        import signal

        old = signal.getsignal(signal.SIGALRM)
        with self.assertRaises(DeadlineReached):
            with deadline(0.01):
                time.sleep(1)
        self.assertEqual(signal.getsignal(signal.SIGALRM), old)


class DemoTests(unittest.TestCase):
    def demo_report(self):
        root = Path(__file__).resolve().parent.parent
        fixture = json.loads((root / "tests/fixtures/demo.json").read_text())
        return run(
            fixture["question"], ReplayModel(fixture["responses"]), Sources(root / "data/corpus")
        )

    def demo_task(self):
        root = Path(__file__).resolve().parent.parent
        return next(task for task in load_tasks(root / "eval/tasks.json") if task["id"] == "dev-01")

    def test_grader_accepts_consistent_demo_but_requires_human_review(self):
        result = grade(self.demo_task(), self.demo_report())
        self.assertTrue(result["mechanical_checks_passed"])
        self.assertTrue(result["requires_human_review"])
        self.assertEqual(result["mode"], "offline_replay")

    def test_grader_rejects_missing_trace(self):
        report = self.demo_report()
        report["events"] = []
        self.assertFalse(grade(self.demo_task(), report)["mechanical_checks_passed"])

    def test_grader_rejects_fabricated_quote(self):
        report = self.demo_report()
        report["answer"]["claims"][0]["citations"][0]["quote"] = "fabricated evidence"
        self.assertFalse(grade(self.demo_task(), report)["mechanical_checks_passed"])

    def test_grader_rejects_altered_source_lines(self):
        report = self.demo_report()
        event = next(
            event
            for event in report["events"]
            if event["event"] == "tool_result" and "lines" in event["result"]
        )
        event["result"]["lines"][0]["text"] = "invented"
        self.assertFalse(grade(self.demo_task(), report)["mechanical_checks_passed"])

    def test_grader_rejects_wrong_units_even_with_consistent_trace(self):
        report = self.demo_report()
        report["answer"]["claims"][0]["unit"] = "USD billion"
        event = [event for event in report["events"] if event["event"] == "model_response"][-1]
        event["response"]["output"][0]["content"][0]["text"] = json.dumps(report["answer"])
        self.assertFalse(grade(self.demo_task(), report)["mechanical_checks_passed"])

    def test_demo_cannot_make_network_requests(self):
        root = Path(__file__).resolve().parent.parent
        fixture = json.loads((root / "tests/fixtures/demo.json").read_text())
        with patch(
            "urllib.request.OpenerDirector.open", side_effect=AssertionError("Network forbidden")
        ):
            report = run(
                fixture["question"],
                ReplayModel(copy.deepcopy(fixture["responses"])),
                Sources(root / "data/corpus"),
            )
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["metrics"]["accounted_cost_usd"], 0)


if __name__ == "__main__":
    unittest.main()
