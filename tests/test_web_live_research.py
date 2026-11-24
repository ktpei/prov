"""Exercise the production live worker with provider responses stubbed at the boundary."""

import hashlib
import os
import queue
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from provenance.controls import Budget
from provenance.exa_sources import EXA_TOOL_SCHEMAS
from provenance.model import ReplayModel
from provenance.web.chat_sources import CHAT_INSTRUCTIONS, ChatSources
from provenance.web.worker import run_turn_process, summarize_event
from tests.test_web_worker import LIMITS, drain

CORPUS = Path(__file__).resolve().parent.parent / "provenance/web/live_sources"
URL = "https://issuer.example/report"
SOURCE_ID = "web-" + hashlib.sha256(URL.encode()).hexdigest()[:16]
ENV = {"EXA_API_KEY": "test-exa-key", "EXA_MAX_REQUEST_USD": "0.03"}


def call(name, **args):
    import json

    return {
        "status": "completed",
        "output": [
            {"type": "function_call", "name": name, "call_id": name, "arguments": json.dumps(args)}
        ],
    }


def answer(source_id):
    import json

    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "answerable": True,
                                "answer": "Revenue was 100.",
                                "claims": [
                                    {
                                        "key": "revenue",
                                        "value": 100,
                                        "unit": "USD million",
                                        "period": "2025",
                                        "citations": [
                                            {
                                                "source_id": source_id,
                                                "locator": "L1",
                                                "quote": "Revenue was 100.",
                                            }
                                        ],
                                    }
                                ],
                            }
                        ),
                    }
                ],
            }
        ],
    }


class LiveResearchTests(unittest.TestCase):
    def test_worker_routes_search_and_reads_through_exa_and_returns_citable_snapshot(self):
        prefix = "session-t1-"
        scoped_id = prefix + SOURCE_ID
        model = ReplayModel(
            [
                call(
                    "search", query="Synthetic issuer revenue", objective="Find the official report"
                ),
                call("read_source", source_id=scoped_id, start_line=1, end_line=2),
                answer(scoped_id),
            ]
        )
        model.mode = "live_openrouter_langchain"
        request = Mock(
            side_effect=[
                {
                    "results": [{"url": URL, "title": "Annual report", "highlights": ["Revenue"]}],
                    "costDollars": {"total": 0.005},
                },
                {
                    "results": [{"url": URL, "text": "Revenue was 100.\nGuidance was 110."}],
                    "costDollars": {"total": 0.001},
                },
            ]
        )
        out = queue.Queue()
        with (
            patch.dict(os.environ, ENV),
            patch("provenance.langchain_model.OpenRouterModel", return_value=model) as model_class,
            patch(
                "provenance.web.chat_sources.ChatSources",
                side_effect=lambda *args, **kwargs: ChatSources(*args, **kwargs, request=request),
            ),
        ):
            run_turn_process(
                {
                    "corpus_dir": str(CORPUS),
                    "source_prefix": prefix,
                    "question_text": "What was revenue?",
                    "limits": LIMITS,
                },
                out,
            )
        terminal, result = drain(out)[-1]
        self.assertEqual(terminal, "done", result)
        self.assertEqual(result["report"]["status"], "completed")
        self.assertAlmostEqual(result["report"]["metrics"]["accounted_cost_usd"], 0.006)
        self.assertEqual(
            result["documents"][scoped_id]["text"], "Revenue was 100.\nGuidance was 110."
        )
        self.assertEqual(
            [c.args[0] for c in request.call_args_list],
            ["https://api.exa.ai/search", "https://api.exa.ai/contents"],
        )
        self.assertEqual(request.call_args_list[0].args[1]["objective"], "Find the official report")
        self.assertEqual(model_class.call_args.kwargs["tool_schemas"], EXA_TOOL_SCHEMAS)
        self.assertEqual(model_class.call_args.kwargs["instructions"], CHAT_INSTRUCTIONS)

    def test_follow_up_must_reread_and_keeps_original_source_text(self):
        source_id = "session-t1-" + SOURCE_ID
        citation = {"source_id": source_id, "locator": "L1", "quote": "Revenue was 100."}
        request = Mock()
        sources = ChatSources(
            CORPUS,
            exa_key="key",
            exa_cap=0.03,
            budget=Budget(0.1),
            source_prefix="session-t2-",
            request=request,
            carried_documents={
                source_id: {"id": source_id, "url": URL, "text": "Revenue was 100."}
            },
        )
        with self.assertRaises(ValueError):
            sources.check_citation(citation)
        sources.call("read_source", {"source_id": source_id, "start_line": 1, "end_line": 1}, 1)
        sources.check_citation(citation)
        request.assert_not_called()

    def test_live_sources_are_scoped_per_turn_and_search_cannot_change_read_snapshot(self):
        request = Mock(
            return_value={
                "results": [{"url": URL, "title": "Report"}],
                "costDollars": {"total": 0.005},
            }
        )
        ids = []
        for prefix in ("session-one-t1-", "session-two-t1-"):
            sources = ChatSources(
                CORPUS,
                exa_key="key",
                exa_cap=0.03,
                budget=Budget(0.1),
                source_prefix=prefix,
                request=request,
            )
            hit = sources.search("revenue", 1, "Find revenue")["results"][0]
            sources.documents[hit["id"]]["text"] = "Original evidence"
            again = sources.search("guidance", 1, "Find guidance")["results"][0]
            self.assertEqual(again["id"], hit["id"])
            self.assertEqual(sources.documents[again["id"]]["text"], "Original evidence")
            ids.append(hit["id"])
        self.assertNotEqual(*ids)

    def test_duplicate_search_results_share_the_same_snapshot(self):
        request = Mock(
            return_value={
                "results": [{"url": URL, "title": "Report"}] * 2,
                "costDollars": {"total": 0.005},
            }
        )
        sources = ChatSources(
            CORPUS,
            exa_key="key",
            exa_cap=0.03,
            budget=Budget(0.1),
            source_prefix="session-t1-",
            request=request,
        )
        hits = sources.search("revenue", 1, "Find revenue")["results"]
        self.assertEqual(hits[0]["id"], hits[1]["id"])
        self.assertEqual(len(sources.documents), 1)

    def test_live_search_summary_has_no_invented_line_numbers(self):
        summary = summarize_event(
            {
                "event": "tool_result",
                "call_id": "search",
                "result": {"results": [{"id": SOURCE_ID, "title": "Report"}]},
            },
            0,
            {"search": ("search", {"query": "revenue"})},
        )
        self.assertIsNone(summary["detail"]["hits"][0]["locator"])

    def test_missing_exa_key_fails_instead_of_loading_demo_evidence(self):
        out = queue.Queue()
        with patch.dict(os.environ, {"EXA_API_KEY": ""}):
            run_turn_process({"corpus_dir": str(CORPUS), "source_prefix": "test-"}, out)
        terminal, error = drain(out)[-1]
        self.assertEqual(terminal, "error")
        self.assertIn("EXA_API_KEY", error)
