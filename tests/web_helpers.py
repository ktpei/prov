"""Offline test doubles for live web routes; never loaded by the application."""

import json
from pathlib import Path

from provenance.agent import Limits
from provenance.model import ReplayModel
from provenance.web.chat_sources import CHAT_INSTRUCTIONS, ChatSources
from provenance.web.workbook import load_snapshot
from provenance.web.worker import StreamingTrace

ROOT = Path(__file__).resolve().parent.parent


def responses_for(question, corpus="cloudflare-2024-q3", snapshot_id=None):
    for entry in json.loads((ROOT / "tests/fixtures/web_research_responses.json").read_text())[
        "scripts"
    ]:
        if entry["corpus"] != corpus or entry["question"] not in question:
            continue
        if entry.get("snapshot_id") and entry["snapshot_id"] != snapshot_id:
            continue
        return entry["responses"]
    return []


def offline_worker(job, queue):
    from provenance.graph import run_graph

    snapshot = (
        load_snapshot(job["workbook_bytes"], job["workbook_filename"])
        if job.get("workbook_bytes")
        else None
    )
    sources = ChatSources(
        ROOT / "data/cloudflare-2024-q3",
        snapshot=snapshot,
        preread_range=job.get("preread"),
    )
    model = ReplayModel(
        job.get("test_responses")
        or responses_for(
            job["question_text"],
            snapshot_id=snapshot.snapshot_id if snapshot else None,
        )
    )
    model.mode = "live_openrouter_langchain"
    trace = StreamingTrace(queue, instructions=CHAT_INSTRUCTIONS, tools=sources.tool_schemas)
    report = run_graph(job["question_text"], model, sources, Limits(**job["limits"]), trace)
    queue.put(
        (
            "done",
            {
                "report": {**report, "model": "test/model"},
                "proposals": sources.proposals,
                "documents": sources.documents,
            },
        )
    )
