"""Run each chat turn in a spawned process and stream summarized progress.

The research runtime enforces wall-clock limits with SIGALRM, which needs a main
thread. A spawned child gives every turn its own main thread, evidence state,
budget, and workbook tools; the parent only reads queue messages.
"""

import json
import multiprocessing
import os
import threading
import time
from pathlib import Path
from queue import Empty

from provenance.agent import Limits, Trace

SCRIPTS = Path(__file__).resolve().parent / "replay_scripts.json"


def _normalize(text):
    return " ".join(str(text).lower().split())


def load_replay_script(question, corpus, *, snapshot_id=None):
    """Return scripted responses for an exact (normalized) question match, else None."""
    for entry in json.loads(SCRIPTS.read_text())["scripts"]:
        if entry["corpus"] != corpus or _normalize(entry["question"]) != _normalize(question):
            continue
        if entry.get("snapshot_id") and entry["snapshot_id"] != snapshot_id:
            continue
        return entry["responses"]
    return None


def _arguments(call):
    try:
        args = json.loads(call.get("arguments") or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return args if isinstance(args, dict) else {}


def summarize_event(event, started, calls):
    """Compact, browser-safe progress row for one runtime trace event (or None)."""
    kind = event.get("event")
    summary = None
    if kind == "run_started":
        summary = ("started", "Research started", {"model": event.get("model")})
    elif kind == "model_response":
        response = event.get("response") or {}
        usage = response.get("usage") or {}
        output = response.get("output") or []
        tools = sum(1 for item in output if item.get("type") == "function_call")
        label = f"Model step {event.get('number')}" + (
            f" → {tools} tool call{'s' if tools != 1 else ''}" if tools else " → answer"
        )
        summary = (
            "model",
            label,
            {
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "tool_calls": tools,
            },
        )
    elif kind == "tool_request":
        call = event.get("call") or {}
        calls[call.get("call_id")] = (call.get("name"), _arguments(call))
    elif kind == "tool_result":
        name, args = calls.get(event.get("call_id"), (None, {}))
        result = event.get("result") or {}
        if "error" in result:
            summary = ("tool_error", f"{name or 'tool'} error", {"error": result["error"]})
        elif name == "search":
            hits = [
                {
                    "source_id": hit.get("id"),
                    "title": hit.get("title"),
                    "locator": f"L{hit.get('start_line')}-L{hit.get('end_line')}",
                }
                for hit in result.get("results", [])[:5]
            ]
            summary = ("search", args.get("query", "search"), {"hits": hits})
        elif name == "read_source":
            summary = (
                "read",
                result.get("title") or result.get("id"),
                {
                    "source_id": result.get("id"),
                    "title": result.get("title"),
                    "locator": result.get("locator"),
                },
            )
        elif name == "read_workbook_range":
            summary = (
                "workbook_read",
                f"{result.get('sheet')}!{result.get('range')}",
                {
                    "sheet": result.get("sheet"),
                    "range": result.get("range"),
                    "cells": len(result.get("cells", [])),
                },
            )
        elif name == "propose_cell_edit":
            summary = (
                "proposal",
                f"Proposed change to {result.get('cell')}",
                {"proposal_id": result.get("proposal_id"), "cell": result.get("cell")},
            )
    elif kind == "tool_call_skipped":
        summary = (
            "tool_error",
            "Tool call skipped at the tool limit",
            {"reason": event.get("reason")},
        )
    elif kind == "final_synthesis_required":
        summary = (
            "final_synthesis",
            "Research limit reached; writing the final answer",
            {"reason": event.get("reason")},
        )
    elif kind == "final_answer_rejected":
        summary = (
            "answer_rejected",
            "Answer rejected by citation checks",
            {"reason": event.get("reason"), "repair_available": event.get("repair_available")},
        )
    elif kind == "run_finished":
        summary = (
            "finished",
            f"Run {event.get('status')}",
            {
                "status": event.get("status"),
                "reason": event.get("reason"),
                "latency_seconds": event.get("latency_seconds"),
            },
        )
    if summary is None:
        return None
    label = summary[1]
    return {
        "kind": summary[0],
        "label": label,
        "detail": summary[2],
        "t": round(max(0.0, time.monotonic() - started), 2) if started else 0.0,
        "cost_usd": event.get("accounted_cost_usd"),
    }


class StreamingTrace(Trace):
    """Trace that records the chat prompt/tools actually sent and streams summaries."""

    def __init__(self, queue, log_dir=None, *, instructions, tools):
        super().__init__(log_dir)
        self.queue, self.instructions, self.tools = queue, instructions, tools
        self.started, self.calls = time.monotonic(), {}

    def emit(self, kind, **fields):
        if kind == "run_started":
            fields.update(instructions=self.instructions, tools=self.tools)
        super().emit(kind, **fields)
        summary = summarize_event(self.events[-1], self.started, self.calls)
        if summary:
            self.queue.put(("event", summary))


def run_turn_process(job, queue):
    """Child-process entry: run one research turn and put exactly one terminal message."""
    try:
        from provenance.graph import run_graph
        from provenance.model import ReplayModel
        from provenance.web.chat_sources import CHAT_INSTRUCTIONS, ChatSources
        from provenance.web.workbook import load_snapshot

        snapshot = (
            load_snapshot(job["workbook_bytes"], job["workbook_filename"])
            if job.get("workbook_bytes")
            else None
        )
        preread = tuple(job["preread"]) if job.get("preread") else None
        sources = ChatSources(job["corpus_dir"], snapshot=snapshot, preread_range=preread)
        if job["mode"] == "replay":
            model = ReplayModel(job["replay_responses"] or [])
        else:
            from provenance.langchain_model import OpenRouterModel

            model = OpenRouterModel(
                os.environ.get("OPENROUTER_API_KEY"),
                os.environ.get("OPENROUTER_MODEL"),
                os.environ.get("OPENROUTER_INPUT_USD_PER_MILLION"),
                os.environ.get("OPENROUTER_OUTPUT_USD_PER_MILLION"),
                max_output=4000,
                instructions=CHAT_INSTRUCTIONS,
                tool_schemas=sources.tool_schemas,
            )
        trace = StreamingTrace(
            queue, job.get("log_dir"), instructions=CHAT_INSTRUCTIONS, tools=sources.tool_schemas
        )
        report = run_graph(job["question_text"], model, sources, Limits(**job["limits"]), trace)
        keep = ("run_id", "mode", "status", "stop_reason", "answer", "metrics")
        queue.put(
            (
                "done",
                {
                    "report": {**{key: report[key] for key in keep}, "model": model.name},
                    "proposals": sources.proposals,
                },
            )
        )
    except Exception as exc:  # noqa: BLE001 - reported to the browser as a failed turn
        queue.put(("error", f"{type(exc).__name__}: {exc}"))


class Turn:
    def __init__(self, turn_id):
        self.id = turn_id
        self.events = []
        self.result = None
        self.error = None
        self.done = threading.Event()


class TurnRunner:
    """Parent side: spawn a worker per turn and collect its messages on a thread."""

    def __init__(self, target=run_turn_process):
        self.context = multiprocessing.get_context("spawn")
        self.target = target

    def start(self, job, on_finish=None):
        queue = self.context.Queue()
        process = self.context.Process(target=self.target, args=(job, queue), daemon=True)
        process.start()
        turn = Turn(job["turn_id"])
        threading.Thread(
            target=self._collect, args=(turn, process, queue, job, on_finish), daemon=True
        ).start()
        return turn

    def _collect(self, turn, process, queue, job, on_finish):
        deadline = time.monotonic() + float(job["limits"]["timeout_seconds"]) + 30
        exited_at = None
        while True:
            try:
                kind, payload = queue.get(timeout=0.25)
            except Empty:
                if not process.is_alive():
                    exited_at = exited_at or time.monotonic()
                    if time.monotonic() - exited_at > 1.0:  # allow the feeder to flush
                        turn.error = "worker_crashed"
                        break
                elif time.monotonic() > deadline:
                    process.terminate()
                    turn.error = "worker_timeout"
                    break
                continue
            if kind == "event":
                turn.events.append(payload)
            elif kind == "done":
                turn.result = payload
                break
            else:
                turn.error = str(payload)
                break
        process.join(timeout=5)
        try:
            if on_finish:
                on_finish(turn)
        finally:
            turn.done.set()
