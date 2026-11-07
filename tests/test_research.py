"""Extraction/retrieval and provider boundaries; no paid model calls."""

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from provenance.agent import Limits, run
from provenance.controls import Budget, LimitReached
from provenance.ingestion import ingest_packet
from provenance.model import ReplayModel
from provenance.openrouter import OpenRouterModel, chat_messages
from provenance.sources import Sources
from provenance.transport import ProviderError

ROOT = Path(__file__).resolve().parent.parent


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.packet = {
            "documents": [
                {
                    "id": "acme-q3",
                    "title": "Acme Q3 presentation",
                    "company": "Acme",
                    "ticker": "ACME",
                    "url": "https://example.com/q3.pdf",
                    "published": "2024-11-07",
                    "source_type": "investor_presentation",
                    "pages": [
                        {"page": 1, "text": "Overview\n" * 90},
                        {
                            "page": 7,
                            "text": "Margin guidance\nPeriod | Non-GAAP margin\nQ4 | 20%\nExcludes restructuring.",
                        },
                    ],
                }
            ]
        }
        self.input = self.root / "input.json"
        self.output = self.root / "packet"

    def ingest(self):
        self.input.write_text(json.dumps(self.packet))
        return ingest_packet(self.input, self.output)

    def test_late_page_search_read_and_citation_keep_original_page(self):
        self.ingest()
        sources = Sources(self.output)
        hit = sources.search("Q4 margin guidance", 1)["results"][0]
        self.assertEqual(hit["match_locator"], "L81-L94")
        result = sources.read(hit["id"], 91, 94, 1)
        self.assertEqual(result["original_pages"], [7])
        self.assertIsNone(result["next_start_line"])
        self.assertIn("Period | Non-GAAP margin", str(result["lines"]))
        sources.check_citation({"source_id": hit["id"], "locator": "L93", "quote": "Q4 | 20%"})
        first = sources.read(hit["id"], 1, 80, 1)
        self.assertEqual(first["next_start_line"], 81)

    def test_search_can_repeat_before_web_content_is_loaded(self):
        self.ingest()
        sources = Sources(self.output)
        sources.documents["web-unread"] = {
            "id": "web-unread",
            "title": "Pending web result",
            "text": None,
        }
        self.assertTrue(sources.search("margin", 1)["results"])
        self.assertTrue(sources.search("guidance", 1)["results"])

    def test_existing_snapshot_is_never_overwritten(self):
        self.ingest()
        original = (self.output / "sources.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.ingest()
        self.assertEqual((self.output / "sources.json").read_bytes(), original)

    def test_bad_pages_and_path_traversal_do_not_create_packet(self):
        for mutate in (
            lambda doc: doc.update(id="../escape"),
            lambda doc: doc["pages"][1].update(page=1),
            lambda doc: doc["pages"][1].update(text=""),
        ):
            packet = copy.deepcopy(self.packet)
            mutate(packet["documents"][0])
            self.input.write_text(json.dumps(packet))
            with self.assertRaises(ValueError):
                ingest_packet(self.input, self.output)
            self.assertFalse(self.output.exists())


class OpenRouterTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.bound = self.client.bind_tools.return_value
        self.response = SimpleNamespace(
            usage_metadata={"input_tokens": 100, "output_tokens": 20},
            invalid_tool_calls=[],
            tool_calls=[],
            content='{"answerable":false}',
            response_metadata={"finish_reason": "stop"},
        )
        self.bound.invoke.return_value = self.response
        self.model = OpenRouterModel("test-key", "test/model", 1, 2, client=self.client)

    def test_tool_round_trip_and_usage_accounting(self):
        self.response.tool_calls = [{"id": "c1", "name": "search", "args": {"query": "Acme"}}]
        self.response.response_metadata = {"finish_reason": "tool_calls"}
        budget = Budget(1)
        response = self.model.step([{"role": "user", "content": "Question"}], 3, budget)
        converted = chat_messages(
            [
                {"role": "user", "content": "Question"},
                *response["output"],
                {"type": "function_call_output", "call_id": "c1", "output": '{"results":[]}'},
            ]
        )
        self.assertEqual(converted[-2]["tool_calls"][0]["function"]["name"], "search")
        self.assertEqual(converted[-1]["tool_call_id"], "c1")
        self.assertAlmostEqual(budget.charged, 0.00014)
        self.assertFalse(budget.uncertain)
        self.assertEqual(self.bound.invoke.call_args.kwargs["timeout"], 3)

    def test_budget_prevents_provider_call(self):
        with self.assertRaises(LimitReached):
            self.model.step([], 1, Budget(0.000001))
        self.bound.invoke.assert_not_called()

    def test_missing_usage_retains_reservation_and_marks_uncertainty(self):
        self.response.usage_metadata = None
        budget = Budget(1)
        with self.assertRaisesRegex(ProviderError, "usage"):
            self.model.step([], 1, budget)
        self.assertGreater(budget.charged, 0)
        self.assertTrue(budget.uncertain)

    def test_provider_errors_do_not_leak_secrets(self):
        self.bound.invoke.side_effect = RuntimeError("Authorization: Bearer secret")
        budget = Budget(1)
        with self.assertRaisesRegex(ProviderError, "reservation retained") as caught:
            self.model.step([], 1, budget)
        self.assertNotIn("secret", str(caught.exception))
        self.assertTrue(budget.uncertain)

    def test_truncated_and_malformed_responses_are_rejected(self):
        for finish, invalid in (("length", []), ("tool_calls", [{"error": "bad JSON"}])):
            self.response.response_metadata = {"finish_reason": finish}
            self.response.invalid_tool_calls = invalid
            with self.assertRaises(ProviderError):
                self.model.step([], 1, Budget(1))


@unittest.skipUnless(importlib.util.find_spec("langgraph"), "LangGraph dependency not installed")
class GraphTests(unittest.TestCase):
    def execute(self, **limits):
        fixture = json.loads((ROOT / "tests/fixtures/demo.json").read_text())
        return run(
            fixture["question"],
            ReplayModel(fixture["responses"]),
            Sources(ROOT / "data/corpus"),
            Limits(**limits),
            runtime="langgraph",
        )

    def test_offline_graph_preserves_evidence_trace(self):
        from provenance.evaluation import grade, load_tasks

        report = self.execute()
        task = next(t for t in load_tasks(ROOT / "eval/tasks.json") if t["id"] == "dev-01")
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["runtime"], "langgraph")
        self.assertTrue(grade(task, report)["mechanical_checks_passed"])

    def test_graph_enforces_call_limits(self):
        self.assertEqual(self.execute(max_model_calls=1)["stop_reason"], "model_call_limit")
        self.assertEqual(self.execute(max_tool_calls=1)["stop_reason"], "tool_call_limit")
