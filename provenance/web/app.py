"""FastAPI backend for the browser MVP: chat turns, evidence, workbooks, exports."""

import asyncio
import hashlib
import hmac
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from provenance.controls import positive
from provenance.sources import Sources
from provenance.web.chat_sources import CONTEXT_LIMIT, compose_question
from provenance.web.ledger import Ledger
from provenance.web.workbook import MAX_BYTES, WorkbookError, export_copy, load_snapshot
from provenance.web.worker import TurnRunner, load_replay_script

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "web/dist"
DEMO_WORKBOOK = ROOT / "data/demo/cloudflare-fy2024-model.xlsx"
TURN_LIMITS = {
    "max_model_calls": 8,
    "max_tool_calls": 10,
    "timeout_seconds": 120,
    "request_timeout_seconds": 30,
}
CORPORA = {
    "cloudflare-2024-q3": {
        "dir": ROOT / "data/cloudflare-2024-q3",
        "label": "Cloudflare Q3 2024 packet",
        "description": "Q3 2024 release, 10-Q, earnings call transcript, and May 2024 investor day deck",
        "starters": [
            "What revenue did Cloudflare report for Q3 2024, and what full-year 2024 revenue "
            "guidance did management give?",
            "What revenue and non-GAAP operating income guidance did Cloudflare give for Q4 2024?",
            "What did management say on the Q3 2024 call about the go-to-market transformation?",
        ],
        "workbook_starters": [
            "Does the FY2024 revenue assumption in my model match management's latest guidance? "
            "If not, propose an update.",
        ],
    },
    "earnings-excerpts": {
        "dir": ROOT / "data/corpus",
        "label": "Big Tech earnings excerpts",
        "description": "Curated official excerpts for Apple, Microsoft, NVIDIA, Amazon, and Meta",
        "starters": [
            "What was Apple's GAAP total net sales in FY2024?",
            "What were NVIDIA's GAAP and non-GAAP diluted EPS for Q3 fiscal 2025?",
            "Compare Meta's Q3 2024 revenue with NVIDIA's Q3 fiscal 2025 revenue.",
            "What revenue guidance did Apple give for Q1 fiscal 2025 in the supplied excerpt?",
        ],
        "workbook_starters": [],
    },
}


class SessionBody(BaseModel):
    corpus: str


class TurnBody(BaseModel):
    question: str
    mode: str = "live"


class ContextBody(BaseModel):
    sheet: str
    range: str


class LoginBody(BaseModel):
    code: str


class ExportBody(BaseModel):
    snapshot_id: str
    proposal_ids: list[str]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _live_settings():
    names = (
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_INPUT_USD_PER_MILLION",
        "OPENROUTER_OUTPUT_USD_PER_MILLION",
    )
    values = [os.environ.get(name, "").strip() for name in names]
    if not all(values):
        return None
    try:
        positive(values[2], "input rate")
        positive(values[3], "output rate")
    except (TypeError, ValueError):
        return None
    return {"model": values[1]}


class Session:
    def __init__(self, corpus):
        self.id = uuid.uuid4().hex[:12]
        self.corpus = corpus
        self.turns = []
        self.live = {}
        self.snapshot = None
        self.context = None
        self.proposals = {}
        self.exports = []
        self.running = None
        self.lock = threading.Lock()

    def view(self):
        return {
            "id": self.id,
            "corpus": self.corpus,
            "turns": list(self.turns),
            "workbook": self.snapshot.info() if self.snapshot else None,
            "context": self.context,
            "proposals": list(self.proposals.values()),
            "exports": list(self.exports),
        }


def create_app(*, replay=False, ledger_path=None, cap_usd=None, runner=None, export_dir=None):
    app = FastAPI(title="Provenance research chat")
    ledger = Ledger(
        ledger_path or os.environ.get("WEB_LEDGER") or ROOT / "runs/web/cost-log.jsonl",
        cap_usd if cap_usd is not None else float(os.environ.get("WEB_SPEND_CAP_USD") or 1.0),
    )
    runner = runner or TurnRunner(prewarm=True)
    export_root = Path(export_dir or ROOT / "runs/web/exports")
    log_root = ROOT / "runs/web/traces"
    sessions, exports = {}, {}
    corpora = {key: Sources(spec["dir"]) for key, spec in CORPORA.items()}
    access_code = (os.environ.get("WEB_ACCESS_CODE") or "").strip()
    access_token = (
        hmac.new(access_code.encode(), b"provenance-web-v1", hashlib.sha256).hexdigest()
        if access_code
        else None
    )

    def authenticated(request):
        if not access_token:
            return True
        return hmac.compare_digest(
            request.cookies.get("prov_access", "").encode(), access_token.encode()
        )

    @app.middleware("http")
    async def access_gate(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and path not in ("/api/auth", "/api/login"):
            if not authenticated(request):
                return JSONResponse(
                    {"detail": "Enter the access code to use this demo"}, status_code=401
                )
        return await call_next(request)

    @app.get("/api/auth")
    def auth_status(request: Request):
        return {"required": bool(access_token), "authenticated": authenticated(request)}

    @app.post("/api/login")
    async def login(body: LoginBody):
        if not access_token:
            return {"ok": True}
        if not hmac.compare_digest(body.code.strip().encode(), access_code.encode()):
            await asyncio.sleep(0.5)
            raise HTTPException(401, "That access code is not right")
        response = JSONResponse({"ok": True})
        response.set_cookie(
            "prov_access", access_token, httponly=True, samesite="lax", max_age=12 * 3600
        )
        return response

    def corpus_view(key):
        spec, documents = CORPORA[key], corpora[key].documents.values()
        return {
            "id": key,
            "label": spec["label"],
            "description": spec["description"],
            "cutoff": max(doc.get("published") or "" for doc in documents),
            "documents": [
                {
                    "id": doc["id"],
                    "title": doc.get("title"),
                    "published": doc.get("published"),
                    "url": doc.get("url"),
                    "has_original": bool(doc.get("original_file")),
                }
                for doc in documents
            ],
            "starters": spec["starters"],
            "workbook_starters": spec["workbook_starters"],
        }

    def session_or_404(sid):
        if sid not in sessions:
            raise HTTPException(404, "Conversation not found; start a new one")
        return sessions[sid]

    def document_or_404(corpus, source_id):
        if corpus not in corpora or source_id not in corpora[corpus].documents:
            raise HTTPException(404, "Unknown source")
        return corpora[corpus].documents[source_id]

    @app.get("/api/config")
    def config():
        live = _live_settings()
        return {
            "live_available": bool(live),
            "replay": replay,
            "model": live["model"] if live else None,
            "spend": {
                "total_usd": round(ledger.total(), 6),
                "cap_usd": ledger.cap,
                "remaining_usd": round(ledger.remaining(), 6),
            },
            "limits": {**TURN_LIMITS, "max_turn_usd": 0.10},
            "corpora": [corpus_view(key) for key in CORPORA],
        }

    @app.post("/api/sessions")
    def create_session(body: SessionBody):
        if body.corpus not in CORPORA:
            raise HTTPException(404, "Unknown evidence set")
        session = Session(body.corpus)
        sessions[session.id] = session
        return session.view()

    @app.get("/api/sessions/{sid}")
    def get_session(sid: str):
        return session_or_404(sid).view()

    @app.get("/api/sources/{corpus}/{source_id}")
    def source_window(corpus: str, source_id: str, start: int = 1, end: int = 60):
        document = document_or_404(corpus, source_id)
        if start < 1 or end < start or end - start + 1 > 200:
            raise HTTPException(400, "Request 1–200 lines with start <= end")
        lines = document["text"].splitlines()
        locations = document.get("line_locations") or []
        end = min(end, len(lines))
        return {
            "id": source_id,
            "title": document.get("title"),
            "url": document.get("url"),
            "published": document.get("published"),
            "total_lines": len(lines),
            "locator_note": document.get(
                "locator_note", "Lines in extracted text; not original page numbers"
            ),
            "has_original": bool(document.get("original_file")),
            "original_type": Path(document["original_file"]).suffix.lstrip(".")
            if document.get("original_file")
            else None,
            "lines": [
                {
                    "line": number,
                    "text": lines[number - 1],
                    "location": locations[number - 1] if locations else None,
                }
                for number in range(start, end + 1)
            ],
        }

    @app.get("/api/sources/{corpus}/{source_id}/original")
    def source_original(corpus: str, source_id: str):
        document = document_or_404(corpus, source_id)
        if not document.get("original_file"):
            raise HTTPException(404, "No archived original for this source; use its public URL")
        path = (CORPORA[corpus]["dir"] / document["original_file"]).resolve()
        if path.suffix.lower() == ".pdf":
            return FileResponse(path, media_type="application/pdf")
        # Archived third-party HTML is untrusted: render it without scripts or same-origin access.
        return FileResponse(
            path, media_type="text/html", headers={"Content-Security-Policy": "sandbox"}
        )

    @app.post("/api/sessions/{sid}/workbook")
    async def upload_workbook(sid: str, file: Annotated[UploadFile, File()]):
        session = session_or_404(sid)
        data = await file.read(MAX_BYTES + 1)
        try:
            snapshot = load_snapshot(data, file.filename or "workbook.xlsx")
        except WorkbookError as exc:
            raise HTTPException(400, str(exc)) from exc
        return attach(session, snapshot)

    def attach(session, snapshot):
        with session.lock:
            session.snapshot, session.context = snapshot, None
            for proposal in session.proposals.values():
                if proposal["status"] == "pending":
                    proposal["status"] = "stale"
        return snapshot.info()

    @app.post("/api/sessions/{sid}/workbook/demo")
    def demo_workbook(sid: str):
        session = session_or_404(sid)
        return attach(session, load_snapshot(DEMO_WORKBOOK.read_bytes(), DEMO_WORKBOOK.name))

    @app.get("/api/sessions/{sid}/workbook/{sheet}")
    def workbook_grid(sid: str, sheet: str):
        session = session_or_404(sid)
        if not session.snapshot:
            raise HTTPException(404, "No workbook uploaded")
        try:
            return session.snapshot.grid(sheet)
        except WorkbookError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.put("/api/sessions/{sid}/context")
    def set_context(sid: str, body: ContextBody):
        session = session_or_404(sid)
        if not session.snapshot:
            raise HTTPException(400, "Upload a workbook before selecting a range")
        try:
            cells = session.snapshot.cells(body.sheet, body.range, CONTEXT_LIMIT)
        except WorkbookError as exc:
            raise HTTPException(400, str(exc)) from exc
        session.context = {"sheet": body.sheet, "range": body.range.upper().replace("$", "")}
        return {**session.context, "cells": len(cells)}

    @app.delete("/api/sessions/{sid}/context")
    def clear_context(sid: str):
        session_or_404(sid).context = None
        return {"sheet": None, "range": None, "cells": 0}

    def finish(session, record, job, turn):
        result, error = turn.result, turn.error
        report = (result or {}).get("report") or {}
        metrics = report.get("metrics") or {}
        with session.lock:
            if error:
                record.update(status="failed", stop_reason=error)
            else:
                record.update(
                    status=report.get("status"),
                    stop_reason=report.get("stop_reason"),
                    mode=report.get("mode"),
                    model=report.get("model"),
                    answer=report.get("answer"),
                    metrics=metrics,
                    run_id=report.get("run_id"),
                )
                for proposal in result.get("proposals", []):
                    pid = f"{record['id']}-{proposal['proposal_id']}"
                    session.proposals[pid] = {
                        "id": pid,
                        "turn_id": record["id"],
                        "snapshot_id": session.snapshot.snapshot_id if session.snapshot else None,
                        "sheet": proposal["sheet"],
                        "cell": proposal["cell"],
                        "old_display": proposal["old_display"],
                        "old_formula": proposal["old_formula"],
                        "new_content": proposal["new_content"],
                        "rationale": proposal["rationale"],
                        "citations": proposal["citations"],
                        "status": "pending",
                    }
                    record["proposal_ids"].append(pid)
            session.running = None
        if job["mode"] == "live":
            cost = metrics.get("accounted_cost_usd")
            uncertain = bool(metrics.get("cost_uncertain")) or cost is None
            ledger.record(
                record["id"],
                job["limits"]["budget_usd"] if cost is None else cost,
                uncertain=uncertain,
                model=record.get("model"),
                mode="live",
                status=record["status"],
            )
        else:
            ledger.record(
                record["id"],
                0.0,
                uncertain=False,
                model="replay",
                mode="replay",
                status=record["status"],
            )

    @app.post("/api/sessions/{sid}/turns")
    def start_turn(sid: str, body: TurnBody):
        session = session_or_404(sid)
        question = body.question.strip()
        if not question or len(question) > 4000:
            raise HTTPException(400, "Questions must contain 1–4000 characters")
        if body.mode not in ("live", "replay"):
            raise HTTPException(400, "mode must be live or replay")
        snapshot = session.snapshot
        responses, budget = None, 0.10
        if body.mode == "replay":
            responses = load_replay_script(
                question, session.corpus, snapshot_id=snapshot.snapshot_id if snapshot else None
            )
            if responses is None:
                raise HTTPException(
                    404,
                    "No scripted replay for this question. Use a starter question or switch "
                    "to live mode.",
                )
        else:
            live = _live_settings()
            if not live:
                raise HTTPException(
                    409, "Live model is not configured (set OPENROUTER_API_KEY in .env)"
                )
            budget = ledger.turn_budget()
            if budget is None:
                raise HTTPException(
                    409,
                    f"Live spend cap reached (${ledger.total():.4f} of ${ledger.cap:.2f} used)",
                )
        with session.lock:
            if session.running:
                raise HTTPException(409, "A question is already running in this conversation")
            history = [t for t in session.turns if t["status"] != "running"]
            turn_id = f"t{len(session.turns) + 1}"
            context = session.context if snapshot else None
            record = {
                "id": turn_id,
                "question": question,
                "status": "running",
                "stop_reason": None,
                "mode": "offline_replay" if body.mode == "replay" else "live_openrouter_langchain",
                "model": None,
                "answer": None,
                "metrics": None,
                "proposal_ids": [],
                "carried": {
                    "turns": min(3, len(history)),
                    "workbook_range": f"{context['sheet']}!{context['range']}" if context else None,
                    "snapshot_id": snapshot.snapshot_id if snapshot else None,
                },
                "started_at": _now(),
            }
            spec = CORPORA[session.corpus]
            job = {
                "turn_id": turn_id,
                "question_text": compose_question(
                    question,
                    corpus_label=spec["label"],
                    cutoff=corpus_view(session.corpus)["cutoff"],
                    history=history,
                    snapshot=snapshot,
                    context=context,
                ),
                "corpus_dir": str(spec["dir"]),
                "mode": body.mode,
                "replay_responses": responses,
                "workbook_bytes": snapshot.data if snapshot else None,
                "workbook_filename": snapshot.filename if snapshot else None,
                "preread": (context["sheet"], context["range"]) if context else None,
                "limits": {**TURN_LIMITS, "budget_usd": budget},
                "log_dir": str(log_root),
            }
            session.turns.append(record)
            session.running = turn_id
        session.live[turn_id] = runner.start(
            job, on_finish=lambda turn: finish(session, record, job, turn)
        )
        return {"turn_id": turn_id}

    @app.get("/api/sessions/{sid}/turns/{tid}/progress")
    def turn_progress(sid: str, tid: str, after: int = -1):
        """Polling alternative to the event stream; works through buffering proxies."""
        session = session_or_404(sid)
        turn = session.live.get(tid)
        record = next((t for t in session.turns if t["id"] == tid), None)
        if turn is None or record is None:
            raise HTTPException(404, "Unknown turn")
        done = turn.done.is_set()
        events = list(turn.events)
        start = max(0, after + 1)
        return {
            "events": [{"id": index, **events[index]} for index in range(start, len(events))],
            "done": done,
            "turn": record if done else None,
        }

    @app.get("/api/sessions/{sid}/turns/{tid}/events")
    async def turn_events(sid: str, tid: str, request: Request):
        session = session_or_404(sid)
        turn = session.live.get(tid)
        record = next((t for t in session.turns if t["id"] == tid), None)
        if turn is None or record is None:
            raise HTTPException(404, "Unknown turn")
        try:
            index = int(request.headers.get("last-event-id", "-1")) + 1
        except ValueError:
            index = 0

        async def stream():
            nonlocal index
            while True:
                finished = turn.done.is_set()
                while index < len(turn.events):
                    data = json.dumps(turn.events[index])
                    yield f"id: {index}\nevent: progress\ndata: {data}\n\n"
                    index += 1
                if finished:
                    yield f"event: done\ndata: {json.dumps(record)}\n\n"
                    return
                if await request.is_disconnected():
                    return
                await asyncio.sleep(0.15)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/sessions/{sid}/exports")
    def create_export(sid: str, body: ExportBody):
        session = session_or_404(sid)
        snapshot = session.snapshot
        ids = sorted(set(body.proposal_ids))
        with session.lock:
            if not snapshot or body.snapshot_id != snapshot.snapshot_id:
                raise HTTPException(
                    409, "The workbook changed since these proposals; ask again on the current file"
                )
            if not ids or any(pid not in session.proposals for pid in ids):
                raise HTTPException(409, "Unknown or missing proposals")
            existing = next(
                (
                    e
                    for e in session.exports
                    if e["snapshot_id"] == body.snapshot_id and sorted(e["proposal_ids"]) == ids
                ),
                None,
            )
            if existing:
                return existing
            chosen = [session.proposals[pid] for pid in ids]
            if any(
                p["status"] == "stale" or p["snapshot_id"] != snapshot.snapshot_id for p in chosen
            ):
                raise HTTPException(409, "Stale proposals cannot be exported")
            cells = [(p["sheet"], p["cell"]) for p in chosen]
            if len(set(cells)) != len(cells):
                raise HTTPException(409, "Choose one proposal per cell")
            titles = {
                doc["id"]: doc.get("title") for doc in corpora[session.corpus].documents.values()
            }
            titles[f"workbook:{snapshot.snapshot_id}"] = f"Uploaded workbook {snapshot.filename}"
            changes = [{**p, "source_titles": titles} for p in chosen]
            export_id = uuid.uuid4().hex[:10]
            try:
                path = export_copy(
                    snapshot, changes, export_root / session.id / export_id, approved_at=_now()
                )
            except WorkbookError as exc:
                raise HTTPException(500, f"Export failed and was discarded: {exc}") from exc
            record = {
                "id": export_id,
                "filename": path.name,
                "snapshot_id": snapshot.snapshot_id,
                "proposal_ids": ids,
                "changes": [
                    {
                        "cell": f"{p['sheet']}!{p['cell']}",
                        "old": p["old_formula"] or p["old_display"],
                        "new": p["new_content"],
                    }
                    for p in chosen
                ],
                "created_at": _now(),
                "download_url": f"/api/exports/{export_id}/download",
            }
            session.exports.append(record)
            exports[export_id] = path
            for proposal in chosen:
                proposal["status"] = "exported"
        return record

    @app.get("/api/exports/{export_id}/download")
    def download_export(export_id: str):
        if export_id not in exports or not exports[export_id].exists():
            raise HTTPException(404, "Unknown export")
        path = exports[export_id]
        return FileResponse(
            path,
            filename=path.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    if DIST.exists():
        app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
    return app
