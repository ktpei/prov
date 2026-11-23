"""Navigation regression cases use invented documents, never evaluation answers."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from provenance.context import project_messages, tool_result_chars
from provenance.controls import Budget, LimitReached
from provenance.daloopa_run import NavigableBenchmarkSources
from provenance.document_navigation import DOCUMENT_CHAR_LIMIT, NavigableExaSources


class DocumentNavigationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "sources.json").write_text('{"sources": []}')
        self.raw = "General discussion of operations.\n" * 1000
        self.raw += "FY2024 USD million\nOrbital widget revenue: 123\n"
        self.url = "https://issuer.example/filing"
        self.request = Mock(
            return_value={
                "results": [{"url": self.url, "text": self.raw}],
                "statuses": [{"id": self.url, "status": "success"}],
                "costDollars": {"total": 0.001},
            }
        )
        self.sources = NavigableExaSources(
            self.root,
            exa_key="synthetic",
            exa_cap=0.03,
            budget=Budget(1),
            request=self.request,
        )
        self.sources.documents["example"] = {
            "id": "example",
            "url": self.url,
            "title": "Example",
            "text": None,
        }

    def test_find_reaches_beyond_old_prefix_then_requires_read(self):
        found = self.sources.call(
            "find_in_source", {"source_id": "example", "query": "orbital widget revenue"}, 5
        )
        match = found["matches"][0]
        self.assertGreater(match["start_line"], 900)
        self.assertEqual(self.sources.seen, {})
        citation = {
            "source_id": "example",
            "locator": "L1002",
            "quote": "Orbital widget revenue: 123",
        }
        with self.assertRaisesRegex(ValueError, "unread"):
            self.sources.check_citation(citation)
        read = self.sources.read("example", match["start_line"], match["end_line"], 5)
        self.sources.check_citation(citation)
        self.assertEqual(found["sha256"], read["sha256"])
        again = self.sources.find("example", "revenue", 5)
        self.assertEqual(again["sha256"], found["sha256"])
        self.request.assert_called_once()
        self.assertEqual(
            self.request.call_args.args[1]["text"]["maxCharacters"], DOCUMENT_CHAR_LIMIT
        )

    def test_read_is_bounded_and_continuation_explicit(self):
        read = self.sources.read("example", 1, 80, 5)
        self.assertEqual(len(read["lines"]), 30)
        self.assertEqual(read["next_start_line"], 31)
        self.assertFalse(read["context_complete"])
        self.assertLess(len(json.dumps(read)), 10000)

    def test_unknown_or_malformed_calls_do_not_fetch(self):
        for args in (
            {"source_id": "unknown", "query": "revenue"},
            {"source_id": "example", "query": ""},
            {"source_id": [], "query": "revenue"},
            {"source_id": "example", "query": "a" * 501},
            {},
        ):
            self.assertIn("error", self.sources.call("find_in_source", args, 5))
        self.request.assert_not_called()

    def test_no_match_is_not_full_document_absence(self):
        found = self.sources.find("example", "unmatched", 5)
        self.assertEqual(found["matches"], [])
        self.assertFalse(found["context_complete"])

    def test_cap_is_reported_and_cache_immutable(self):
        self.request.return_value["results"][0]["text"] = "x" * (DOCUMENT_CHAR_LIMIT + 10)
        found = self.sources.find("example", "revenue", 5)
        self.assertTrue(found["extraction_at_character_limit"])
        read = self.sources.read("example", 1, 30, 5)
        self.assertTrue(read["extraction_at_character_limit"])
        self.assertEqual(read["sha256"], found["sha256"])
        self.request.assert_called_once()

    def test_provider_failure_settles_charge_without_marking_seen(self):
        self.request.return_value["statuses"][0]["status"] = "error"
        result = self.sources.call(
            "find_in_source", {"source_id": "example", "query": "revenue"}, 5
        )
        self.assertIn("error", result)
        self.assertAlmostEqual(self.sources.budget.charged, 0.001)
        self.assertFalse(self.sources.budget.uncertain)
        self.assertEqual(self.sources.seen, {})

    def test_budget_exhaustion_prevents_dispatch(self):
        self.sources.budget = Budget(0.001)
        with self.assertRaises(LimitReached):
            self.sources.find("example", "revenue", 5)
        self.request.assert_not_called()

    def test_reserved_metadata_cannot_be_fetched_through_find(self):
        guarded = NavigableBenchmarkSources(
            self.root,
            exa_key="synthetic",
            exa_cap=0.03,
            budget=Budget(1),
            request=self.request,
        )
        guarded.documents["reserved"] = {
            "id": "reserved",
            "title": "AMD annual filing",
            "url": self.url,
            "text": None,
        }
        result = guarded.call("find_in_source", {"source_id": "reserved", "query": "revenue"}, 5)
        self.assertIn("Reserved", result["error"])
        self.request.assert_not_called()

    def test_latest_find_survives_large_prior_search_and_read(self):
        messages = []
        for i, (name, size) in enumerate(
            [("search", 24000), ("read_source", 8000), ("find_in_source", 3000)]
        ):
            messages.extend(
                [
                    {"type": "function_call", "call_id": str(i), "name": name},
                    {
                        "type": "function_call_output",
                        "call_id": str(i),
                        "output": json.dumps({"text": "x" * size}),
                    },
                ]
            )
        projected = project_messages(messages)
        self.assertIn("omitted_from_model_context", projected[1]["output"])
        self.assertEqual(projected[3], messages[3])
        self.assertEqual(projected[5], messages[5])
        self.assertLess(tool_result_chars(projected), 32000)
        self.assertNotIn("omitted_from_model_context", messages[1]["output"])
