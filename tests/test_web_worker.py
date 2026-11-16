import json
import queue
import tempfile
import unittest
from pathlib import Path

from provenance.web.ledger import Ledger


class LedgerTests(unittest.TestCase):
    def test_ledger_caps_and_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "cost-log.jsonl"
            ledger = Ledger(path, 0.20)
            self.assertEqual(ledger.turn_budget(), 0.10)
            ledger.record("t1", 0.15, uncertain=False, model="m", mode="live", status="completed")
            self.assertAlmostEqual(ledger.remaining(), 0.05)
            self.assertAlmostEqual(ledger.turn_budget(), 0.05)
            ledger.record("t2", 0.045, uncertain=True, model="m", mode="live", status="failed")
            self.assertIsNone(ledger.turn_budget())
            ledger.record("t3", 0.0, uncertain=False, model="r", mode="replay", status="completed")
            reloaded = Ledger(path, 0.20)
            self.assertAlmostEqual(reloaded.total(), 0.195)
            self.assertEqual(len(path.read_text().splitlines()), 3)


ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data/cloudflare-2024-q3"
FIXTURE = ROOT / "data/demo/cloudflare-fy2024-model.xlsx"
LIMITS = {
    "max_model_calls": 8,
    "max_tool_calls": 10,
    "timeout_seconds": 60,
    "request_timeout_seconds": 30,
    "budget_usd": 0.10,
}
Q1 = (
    "What revenue did Cloudflare report for Q3 2024, and what full-year 2024 revenue "
    "guidance did management give?"
)
Q2 = (
    "Does the FY2024 revenue assumption in my model match management's latest guidance? "
    "If not, propose an update."
)


def crash_target(job, queue):
    import os

    os._exit(3)


def job(question, **overrides):
    from provenance.web.worker import load_replay_script

    snapshot_id = overrides.pop("snapshot_id", None)
    return {
        "turn_id": "t1",
        "question_text": question,
        "corpus_dir": str(CORPUS),
        "mode": "replay",
        "replay_responses": load_replay_script(
            question, "cloudflare-2024-q3", snapshot_id=snapshot_id
        ),
        "workbook_bytes": None,
        "workbook_filename": None,
        "preread": None,
        "limits": LIMITS,
        "log_dir": None,
        **overrides,
    }


def drain(queue):
    messages = []
    while not queue.empty():
        messages.append(queue.get())
    return messages


class WorkerTests(unittest.TestCase):
    def test_summarize_event_kinds(self):
        from provenance.web.worker import summarize_event

        calls = {}
        started = 0.0

        def kind(event):
            summary = summarize_event(event, started, calls)
            return summary and summary["kind"]

        self.assertEqual(kind({"event": "run_started", "model": "m"}), "started")
        self.assertIsNone(kind({"event": "model_request", "number": 1}))
        self.assertEqual(
            kind({"event": "model_response", "number": 1, "response": {"usage": {}}}), "model"
        )
        for call_id, name, args in (
            ("s", "search", {"query": "q"}),
            ("r", "read_source", {"source_id": "x", "start_line": 1, "end_line": 2}),
            ("w", "read_workbook_range", {"sheet": "Model", "range": "B7"}),
            ("p", "propose_cell_edit", {"sheet": "Model", "cell": "B7"}),
            ("e", "search", {"query": "bad"}),
        ):
            call = {"call_id": call_id, "name": name, "arguments": json.dumps(args)}
            self.assertIsNone(kind({"event": "tool_request", "call": call}))
        results = {
            "s": (
                {"results": [{"id": "a", "title": "A", "start_line": 1, "end_line": 9}]},
                "search",
            ),
            "r": ({"id": "x", "title": "X", "locator": "L1-L2"}, "read"),
            "w": ({"sheet": "Model", "range": "B7", "cells": [{}]}, "workbook_read"),
            "p": ({"proposal_id": "P1", "cell": "Model!B7"}, "proposal"),
            "e": ({"error": "nope"}, "tool_error"),
        }
        for call_id, (result, expected) in results.items():
            self.assertEqual(
                kind({"event": "tool_result", "call_id": call_id, "result": result}), expected
            )
        hits = summarize_event(
            {"event": "tool_result", "call_id": "s", "result": results["s"][0]}, started, calls
        )["detail"]["hits"]
        self.assertEqual(hits, [{"source_id": "a", "title": "A", "locator": "L1-L9"}])
        self.assertEqual(
            kind({"event": "final_synthesis_required", "reason": "x"}), "final_synthesis"
        )
        self.assertEqual(kind({"event": "final_answer_rejected", "reason": "x"}), "answer_rejected")
        self.assertEqual(kind({"event": "run_finished", "status": "completed"}), "finished")

    def test_replay_turn_end_to_end(self):
        from provenance.web.worker import run_turn_process

        out = queue.Queue()
        run_turn_process(job(Q1), out)
        messages = drain(out)
        kinds = [payload["kind"] for kind, payload in messages if kind == "event"]
        self.assertIn("search", kinds)
        self.assertIn("read", kinds)
        terminal, payload = messages[-1]
        self.assertEqual(terminal, "done", payload)
        report = payload["report"]
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["mode"], "offline_replay")
        self.assertGreaterEqual(len(report["answer"]["claims"]), 2)
        self.assertEqual(report["metrics"]["accounted_cost_usd"], 0)
        self.assertEqual(payload["proposals"], [])

    def test_replay_workbook_turn_proposes(self):
        from provenance.web.worker import run_turn_process

        data = FIXTURE.read_bytes()
        out = queue.Queue()
        run_turn_process(
            job(
                Q2,
                snapshot_id="a34195a4a257",
                workbook_bytes=data,
                workbook_filename=FIXTURE.name,
            ),
            out,
        )
        terminal, payload = drain(out)[-1]
        self.assertEqual(terminal, "done", payload)
        self.assertEqual(payload["report"]["status"], "completed")
        proposal = payload["proposals"][0]
        self.assertEqual((proposal["cell"], proposal["new_content"]), ("B7", 1661.5))
        sources = {
            c["source_id"]
            for claim in payload["report"]["answer"]["claims"]
            for c in claim["citations"]
        }
        self.assertIn("workbook:a34195a4a257", sources)

    def test_runner_reports_crash(self):
        from provenance.web.worker import TurnRunner

        runner = TurnRunner(target=crash_target)
        turn = runner.start(job(Q1))
        self.assertTrue(turn.done.wait(30))
        self.assertEqual(turn.error, "worker_crashed")
        self.assertIsNone(turn.result)

    def test_runner_real_process_replay(self):
        from provenance.web.worker import TurnRunner

        finished = []
        turn = TurnRunner().start(job(Q1), on_finish=finished.append)
        self.assertTrue(turn.done.wait(60))
        self.assertIsNone(turn.error)
        self.assertEqual(turn.result["report"]["status"], "completed")
        self.assertTrue(any(event["kind"] == "read" for event in turn.events))
        self.assertEqual(finished, [turn])

    def test_runner_prewarm_reuses_standby(self):
        from provenance.web.worker import TurnRunner

        runner = TurnRunner(prewarm=True)
        self.assertIsNotNone(runner.standby)
        warm_pid = runner.standby[0].pid
        first = runner.start(job(Q1))
        self.assertTrue(first.done.wait(60))
        self.assertIsNone(first.error)
        self.assertEqual(first.pid, warm_pid)
        second = runner.start(job(Q1))
        self.assertTrue(second.done.wait(60))
        self.assertIsNone(second.error)
        self.assertNotEqual(second.pid, warm_pid)
        runner.close()

    def test_load_replay_script_match(self):
        from provenance.web.worker import load_replay_script

        self.assertIsNotNone(load_replay_script("  " + Q1.upper() + " ", "cloudflare-2024-q3"))
        self.assertIsNone(load_replay_script(Q1, "earnings-excerpts"))
        self.assertIsNone(load_replay_script(Q2, "cloudflare-2024-q3"))
        self.assertIsNone(load_replay_script(Q2, "cloudflare-2024-q3", snapshot_id="ffffffffffff"))
        self.assertIsNotNone(
            load_replay_script(Q2, "cloudflare-2024-q3", snapshot_id="a34195a4a257")
        )


if __name__ == "__main__":
    unittest.main()
