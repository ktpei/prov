"""Exa request contracts and bounded billing without live network calls."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from provenance.controls import Budget
from provenance.exa_sources import (
    EXA_INSTRUCTIONS,
    EXA_TOOL_SCHEMAS,
    OBJECTIVE_DESCRIPTION,
    ExaSources,
)


class ExaSourcesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "sources.json").write_text(json.dumps({"sources": []}))
        self.request = Mock(
            return_value={
                "results": [
                    {
                        "url": "https://issuer.example/report",
                        "title": "Annual report",
                        "highlights": ["A source highlight"],
                    }
                ],
                "costDollars": {"total": 0.005},
            }
        )
        self.sources = ExaSources(
            self.root,
            exa_key="synthetic-secret",
            exa_cap=0.03,
            budget=Budget(0.1),
            request=self.request,
        )

    def test_model_objective_forwarded_unchanged_and_search_highlights_not_citable(self):
        objective = "Find the official annual report and its revenue table."
        result = self.sources.call(
            "search", {"query": "Synthetic annual report", "objective": objective}, 10
        )
        payload = self.request.call_args.args[1]
        self.assertEqual(
            payload,
            {
                "query": "Synthetic annual report",
                "objective": objective,
                "type": "auto",
                "numResults": 5,
                "contents": {"highlights": True},
            },
        )
        self.assertEqual(result["results"][0]["highlights"], ["A source highlight"])
        self.assertEqual(self.sources.seen, {})
        self.assertAlmostEqual(self.sources.budget.charged, 0.005)
        self.assertNotIn("synthetic-secret", str(result))
        self.assertEqual(
            EXA_TOOL_SCHEMAS[0]["parameters"]["properties"]["objective"]["description"],
            OBJECTIVE_DESCRIPTION,
        )
        self.assertIn("Call search before answering unless", EXA_INSTRUCTIONS)

    def test_missing_objective_does_not_dispatch(self):
        for args in ({"query": "test"}, {"query": "test", "objective": ""}):
            self.assertIn("error", self.sources.call("search", args, 1))
        self.request.assert_not_called()

    def test_http_200_extraction_failure_is_checked_after_cost_settlement(self):
        result = self.sources.call("search", {"query": "test", "objective": "Find evidence"}, 1)
        source_id = result["results"][0]["id"]
        self.request.return_value = {
            "costDollars": {"total": 0.001},
            "results": [],
            "statuses": [{"id": "https://issuer.example/report", "status": "error"}],
        }
        failed = self.sources.call(
            "read_source", {"source_id": source_id, "start_line": 1, "end_line": 2}, 1
        )
        self.assertEqual(failed, {"error": "Exa could not extract the requested source"})
        self.assertAlmostEqual(self.sources.budget.charged, 0.006)
        self.assertFalse(self.sources.budget.uncertain)
        self.assertEqual(
            self.request.call_args.args[1],
            {"urls": ["https://issuer.example/report"], "text": {"maxCharacters": 16000}},
        )
