"""Offline verification of graph limits, provider translation and durable evidence."""

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from langchain_core.messages import AIMessage

from provenance.agent import Limits
from provenance.controls import Budget, LimitReached
from provenance.graph import run_graph
from provenance.langchain_model import OpenRouterModel, chat_messages
from provenance.model import ReplayModel
from provenance.sources import Sources


def response(output):
    return {"status": "completed", "output": output}


def read():
    return response(
        [
            {
                "type": "function_call",
                "name": "read_source",
                "call_id": "r1",
                "arguments": json.dumps({"source_id": "acme", "start_line": 1, "end_line": 1}),
            }
        ]
    )


def answer():
    result = {
        "answerable": True,
        "answer": "Revenue was 120 USD million.",
        "claims": [
            {
                "key": "revenue",
                "value": 120,
                "unit": "USD million",
                "period": "FY2024",
                "citations": [
                    {
                        "source_id": "acme",
                        "locator": "L1",
                        "quote": "Revenue FY2024: 120 USD million.",
                    }
                ],
            }
        ],
    }
    return response(
        [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(result)}]}]
    )


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        text = "Revenue FY2024: 120 USD million.\n"
        (self.root / "acme.txt").write_text(text)
        (self.root / "sources.json").write_text(
            json.dumps(
                {
                    "sources": [
                        {
                            "id": "acme",
                            "title": "Acme results",
                            "text_file": "acme.txt",
                            "sha256": hashlib.sha256(text.encode()).hexdigest(),
                        }
                    ]
                }
            )
        )

    def sources(self):
        return Sources(self.root)

    def test_demo_cli_resume_advances_recorded_fixture_cursor(self):
        command = [
            sys.executable,
            "-m",
            "provenance",
            "demo",
            "--checkpoint",
            str(self.root / "demo.db"),
            "--thread-id",
            "demo-resume",
        ]
        first = subprocess.run(
            command + ["--pause-after-tools"], capture_output=True, text=True, timeout=10
        )
        self.assertEqual(first.returncode, 1, first.stderr)
        paused = json.loads(first.stdout)
        self.assertEqual(paused["status"], "paused")
        self.assertEqual(paused["metrics"]["model_calls"], 1)
        resumed = subprocess.run(command + ["--resume"], capture_output=True, text=True, timeout=10)
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        report = json.loads(resumed.stdout)
        self.assertEqual(report["status"], "completed")
        # Full fixture has exactly search, read, answer. Restarting its cursor
        # would repeat search and inflate these counts to four and three.
        self.assertEqual(report["metrics"]["model_calls"], 3)
        self.assertEqual(report["metrics"]["tool_calls"], 2)
        self.assertEqual(report["run_id"], paused["run_id"])

    def test_graph_preserves_citation_validation(self):
        result = run_graph("Revenue?", ReplayModel([read(), answer()]), self.sources())
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["metrics"]["model_calls"], 2)
        unread = run_graph("Revenue?", ReplayModel([answer(), answer()]), self.sources())
        self.assertEqual(unread["status"], "failed")
        self.assertIn("unread", unread["stop_reason"])

    def invalid_quote(self):
        result = answer()
        claim = json.loads(result["output"][0]["content"][0]["text"])
        claim["claims"][0]["citations"][0]["quote"] = "Revenue FY2024 ... 120 USD million."
        result["output"][0]["content"][0]["text"] = json.dumps(claim)
        return result

    def test_invalid_final_quote_has_one_model_directed_repair(self):
        result = run_graph(
            "Revenue?", ReplayModel([read(), self.invalid_quote(), answer()]), self.sources()
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["metrics"]["model_calls"], 3)
        self.assertEqual(result["metrics"]["answer_retries"], 1)
        rejections = [
            event for event in result["events"] if event["event"] == "final_answer_rejected"
        ]
        self.assertEqual(len(rejections), 1)
        self.assertTrue(rejections[0]["repair_available"])
        requests = [event for event in result["events"] if event["event"] == "model_request"]
        self.assertEqual(requests[-1]["input"][-1]["role"], "user")
        self.assertIn("exact contiguous", requests[-1]["input"][-1]["content"])
        # The rejected raw answer remains inspectable alongside its correction.
        responses = [event for event in result["events"] if event["event"] == "model_response"]
        self.assertIn("...", responses[-2]["response"]["output"][0]["content"][0]["text"])

    def test_repeated_invalid_final_is_terminal(self):
        result = run_graph(
            "Revenue?",
            ReplayModel([read(), self.invalid_quote(), self.invalid_quote(), answer()]),
            self.sources(),
        )
        self.assertEqual(result["status"], "failed")
        self.assertIn("absent", result["stop_reason"])
        self.assertEqual(result["metrics"]["model_calls"], 3)
        self.assertIsNone(result["answer"])
        rejections = [
            event for event in result["events"] if event["event"] == "final_answer_rejected"
        ]
        self.assertEqual([event["repair_available"] for event in rejections], [True, False])

    def test_final_repair_cannot_bypass_model_call_limit(self):
        result = run_graph(
            "Revenue?",
            ReplayModel([read(), self.invalid_quote(), answer()]),
            self.sources(),
            Limits(max_model_calls=2),
        )
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_reason"], "model_call_limit")
        self.assertEqual(result["metrics"]["model_calls"], 2)
        self.assertIsNone(result["answer"])

    def test_repair_can_read_missing_lines_before_answering(self):
        result = run_graph("Revenue?", ReplayModel([answer(), read(), answer()]), self.sources())
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["metrics"]["answer_retries"], 1)
        self.assertEqual(result["metrics"]["tool_calls"], 1)

    def test_last_model_turn_is_reserved_for_supported_final_synthesis(self):
        class FinalModel(ReplayModel):
            def final_step(self, messages, timeout, budget):
                self.final_messages = messages
                return answer()

        model = FinalModel([read()])
        result = run_graph("Revenue?", model, self.sources(), Limits(max_model_calls=2))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["metrics"]["model_calls"], 2)
        self.assertIn("Tool use is disabled", model.final_messages[-1]["content"])
        boundary = next(
            event for event in result["events"] if event["event"] == "final_synthesis_required"
        )
        self.assertEqual(boundary["reason"], "last_model_turn")

    def test_tool_cap_switches_to_final_synthesis_without_extra_tool_calls(self):
        class FinalModel(ReplayModel):
            def final_step(self, messages, timeout, budget):
                return answer()

        result = run_graph(
            "Revenue?",
            FinalModel([read()]),
            self.sources(),
            Limits(max_model_calls=8, max_tool_calls=1),
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["metrics"]["model_calls"], 2)
        self.assertEqual(result["metrics"]["tool_calls"], 1)
        boundary = next(
            event for event in result["events"] if event["event"] == "final_synthesis_required"
        )
        self.assertEqual(boundary["reason"], "tool_call_limit")

    def test_extra_parallel_calls_are_paired_but_not_executed_at_tool_cap(self):
        class FinalModel(ReplayModel):
            def final_step(self, messages, timeout, budget):
                self.final_messages = messages
                return answer()

        parallel = read()
        parallel["output"].append({**parallel["output"][0], "call_id": "r2"})
        model = FinalModel([parallel])
        result = run_graph(
            "Revenue?", model, self.sources(), Limits(max_model_calls=4, max_tool_calls=1)
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["metrics"]["model_calls"], 2)
        self.assertEqual(result["metrics"]["tool_calls"], 1)
        tool_results = [
            message
            for message in model.final_messages
            if message.get("type") == "function_call_output"
        ]
        self.assertEqual([message["call_id"] for message in tool_results], ["r1", "r2"])
        self.assertIn("not executed", tool_results[1]["output"])
        self.assertEqual(sum(event["event"] == "tool_request" for event in result["events"]), 1)
        self.assertEqual(
            sum(event["event"] == "tool_call_skipped" for event in result["events"]), 1
        )

    def test_provider_cannot_execute_tools_after_forced_final_boundary(self):
        class DisobedientModel(ReplayModel):
            def final_step(self, messages, timeout, budget):
                return read()

        result = run_graph(
            "Revenue?", DisobedientModel([]), self.sources(), Limits(max_model_calls=1)
        )
        self.assertEqual(result["status"], "failed")
        self.assertIn("during final synthesis", result["stop_reason"])
        self.assertEqual(result["metrics"]["model_calls"], 1)
        self.assertEqual(result["metrics"]["tool_calls"], 0)

    def test_graph_enforces_model_and_tool_limits(self):
        result = run_graph(
            "Revenue?", ReplayModel([read(), read()]), self.sources(), Limits(max_model_calls=1)
        )
        self.assertEqual(result["stop_reason"], "model_call_limit")
        result = run_graph(
            "Revenue?", ReplayModel([read(), read()]), self.sources(), Limits(max_tool_calls=1)
        )
        self.assertEqual(result["stop_reason"], "tool_call_limit")
        self.assertEqual(result["metrics"]["tool_calls"], 1)

    def test_sqlite_resume_restores_read_evidence_and_counters(self):
        options = {"checkpoint_path": self.root / "state.db", "thread_id": "research-1"}
        first = run_graph(
            "Revenue?", ReplayModel([read()]), self.sources(), pause_after_tools=True, **options
        )
        self.assertEqual(first["status"], "paused")
        second = run_graph(
            "Revenue?", ReplayModel([answer()]), self.sources(), resume=True, **options
        )
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["metrics"]["model_calls"], 2)
        self.assertEqual(second["metrics"]["tool_calls"], 1)
        with self.assertRaisesRegex(ValueError, "differs"):
            run_graph("Different?", ReplayModel([]), self.sources(), resume=True, **options)
        # Completed resume never makes a new model/tool call.
        third = run_graph("Revenue?", ReplayModel([]), self.sources(), resume=True, **options)
        self.assertEqual(third["status"], "completed")
        self.assertEqual(third, second)
        self.assertEqual(first["run_id"], second["run_id"])
        with self.assertRaisesRegex(ValueError, "already exists"):
            run_graph("Revenue?", ReplayModel([]), self.sources(), **options)

    def test_uncommitted_attempt_cannot_be_retried_on_resume(self):
        options = {"checkpoint_path": self.root / "state.db", "thread_id": "crashed"}
        run_graph(
            "Revenue?", ReplayModel([read()]), self.sources(), pause_after_tools=True, **options
        )
        # Simulate death after the next model request starts, before its node
        # commits; the older paused checkpoint still says one model call.
        with sqlite3.connect(str(options["checkpoint_path"])) as connection:
            connection.execute(
                "UPDATE research_attempts SET sequence = 2 WHERE thread_id = ?", ("crashed",)
            )
        with self.assertRaisesRegex(ValueError, "Uncommitted provider attempt"):
            run_graph("Revenue?", ReplayModel([answer()]), self.sources(), resume=True, **options)

    def test_process_death_after_resume_blocks_duplicate_model_request(self):
        options = {"checkpoint_path": self.root / "state.db", "thread_id": "process-death"}
        run_graph(
            "Revenue?", ReplayModel([read()]), self.sources(), pause_after_tools=True, **options
        )
        script = """
import os
import sys
from pathlib import Path
from provenance.graph import run_graph
from provenance.model import ReplayModel
from provenance.sources import Sources
class CrashModel(ReplayModel):
    def step(self, *args):
        os._exit(7)
root = Path(sys.argv[1])
run_graph("Revenue?", CrashModel([]), Sources(root),
          checkpoint_path=root / "state.db", thread_id="process-death", resume=True)
"""
        process = subprocess.run(
            [sys.executable, "-c", script, str(self.root)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(process.returncode, 7, process.stderr)
        with self.assertRaisesRegex(ValueError, "Uncommitted provider attempt"):
            run_graph("Revenue?", ReplayModel([answer()]), self.sources(), resume=True, **options)

    def test_resume_retains_budget_spending(self):
        class SpendModel(ReplayModel):
            def step(self, messages, timeout, budget):
                budget.reserve(0.01)
                return super().step(messages, timeout, budget)

        options = {"checkpoint_path": self.root / "state.db", "thread_id": "budget"}
        run_graph(
            "Revenue?",
            SpendModel([read()]),
            self.sources(),
            Limits(budget_usd=0.015),
            pause_after_tools=True,
            **options,
        )
        resumed = run_graph(
            "Revenue?",
            SpendModel([answer()]),
            self.sources(),
            Limits(budget_usd=0.015),
            resume=True,
            **options,
        )
        self.assertEqual(resumed["stop_reason"], "spend_limit")
        self.assertAlmostEqual(resumed["metrics"]["accounted_cost_usd"], 0.01)


class OpenRouterTests(unittest.TestCase):
    def test_langchain_tool_call_and_usage_translation(self):
        chat = Mock()
        bound = chat.bind_tools.return_value
        bound.bind.return_value.invoke.return_value = AIMessage(
            content="",
            tool_calls=[{"id": "c1", "name": "search", "args": {"query": "Acme"}}],
            usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
            response_metadata={"finish_reason": "tool_calls"},
        )
        model = OpenRouterModel("secret", "test", 1, 2, chat=chat)
        budget = Budget(1)
        result = model.step([{"role": "user", "content": "Revenue?"}], 2, budget)
        self.assertEqual(result["output"][0]["name"], "search")
        self.assertEqual(result["usage"]["input_tokens"], 100)
        self.assertAlmostEqual(budget.charged, 0.00014)
        bound.bind.assert_called_once_with(timeout=2)

    def test_final_step_disables_provider_tools_and_preserves_usage_accounting(self):
        chat = Mock()
        bound = chat.bind_tools.return_value
        bound.bind.return_value.invoke.return_value = AIMessage(
            content='{"answerable":false,"answer":"Missing evidence","claims":[]}',
            usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
            response_metadata={"finish_reason": "stop"},
        )
        model = OpenRouterModel("secret", "test", 1, 2, chat=chat)
        budget = Budget(1)
        result = model.final_step([{"role": "user", "content": "Revenue?"}], 2, budget)
        bound.bind.assert_called_once_with(timeout=2, tool_choice="none")
        self.assertEqual(result["usage"]["input_tokens"], 100)
        self.assertAlmostEqual(budget.charged, 0.00014)

    def test_budget_stops_before_provider_request(self):
        chat = Mock()
        model = OpenRouterModel("secret", "test", 10, 20, chat=chat)
        with self.assertRaises(LimitReached):
            model.step([], 1, Budget(0.000001))
        chat.bind_tools.return_value.bind.assert_not_called()

    def test_parallel_provider_calls_grouped_for_next_turn(self):
        calls = read()["output"]
        calls.append({**calls[0], "call_id": "r2"})
        messages = chat_messages(
            calls
            + [
                {"type": "function_call_output", "call_id": "r1", "output": "{}"},
                {"type": "function_call_output", "call_id": "r2", "output": "{}"},
            ]
        )
        self.assertEqual(len(messages), 4)
        self.assertEqual(len(messages[1].tool_calls), 2)
