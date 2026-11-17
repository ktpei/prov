# Web Chatbot MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local browser app where an analyst researches company evidence with the existing agent, inspects every citation, asks follow-ups, attaches a workbook range, and approves agent-proposed cell edits into a downloadable edited copy.

**Architecture:** A FastAPI app (`provenance/web/`) wraps the existing `run_graph` agent. Each chat turn runs in a spawned child process (SIGALRM deadlines need a main thread); a `StreamingTrace` forwards summarized events over a multiprocessing queue that the API exposes as Server-Sent Events. `ChatSources(Sources)` adds workbook tools and `workbook:` citations without changing base code. A Vite + React + TypeScript + Tailwind frontend (`web/`) is built to `web/dist` and served by the same FastAPI process.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, openpyxl, python-multipart, LangGraph runtime already in repo; React 18, TypeScript, Vite, Tailwind CSS v4 (`@tailwindcss/vite`), Playwright for end-to-end tests.

**Spec:** [docs/web-mvp-design.md](../../web-mvp-design.md)

## Global Constraints

- Do not modify existing modules under `provenance/` except adding `provenance/web/`; existing 440 tests, `corepack yarn lint` and `uv run python -m provenance validate` must stay green.
- Answer contract unchanged: `{"answerable", "answer", "claims"}`; claims `{"key","value","unit","period","citations"}`; citations `{"source_id","locator","quote"}`.
- Per-turn `Limits(max_model_calls=8, max_tool_calls=10, timeout_seconds=120, request_timeout_seconds=30, budget_usd=min(0.10, ledger remaining))`.
- Spend cap `WEB_SPEND_CAP_USD` default `1.00`; ledger file `WEB_LEDGER` default `runs/web/cost-log.jsonl`; refuse live turns when remaining `< 0.01`.
- Workbook limits: `.xlsx` only, ≤ 5 MB, ≤ 30 sheets; grid preview 60 rows × 26 columns; context range ≤ 400 cells; `read_workbook_range` ≤ 200 cells; ≤ 10 proposals per turn.
- Snapshot ID = first 12 hex chars of SHA-256 of uploaded bytes; workbook citation `source_id` = `workbook:<snapshot_id>`, locator `Sheet!B5` or `Sheet!A1:C3`.
- Live model from env: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_INPUT_USD_PER_MILLION`, `OPENROUTER_OUTPUT_USD_PER_MILLION`; the server loads `<repo>/.env` without overriding existing env vars. Keys never reach the browser or logs.
- Replay output is labeled "Scripted replay" wherever it appears. No file is written for the user before explicit approval; uploaded originals are never modified.
- Starter questions and dogfood use Cloudflare, Apple, NVIDIA, Meta only (Amazon/Microsoft are reserved validation issuers).
- Commits: small, plain messages, no attribution trailers (AGENTS.md).

## Review Focus

- A model that cites lines it never read, or quotes a workbook cell value that doesn't match → answer rejected once with repair, then the turn shows `failed` with the validator's reason (never a silently uncited number). Test in Task 2.
- Uploading a second workbook after proposals exist → old proposals show `stale`, cannot be exported; export request for them returns 409. Test in Task 5.
- Approving the same proposal set twice (double click / retry) → same export ID and file, not a second file. Test in Task 5.
- Browser reconnects mid-turn (EventSource auto-reconnect) → no duplicated activity rows; stream resumes after `Last-Event-ID`. Test in Task 5.
- Child process crashes or hangs past the deadline → turn ends `failed` with reason `worker_crashed` / `worker_timeout`, ledger records full reserved budget as uncertain. Test in Task 4.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `provenance/web/__init__.py` | Package marker |
| `provenance/web/workbook.py` | Snapshot load, A1 parsing, grid/range reads, display formatting, export with verification |
| `provenance/web/chat_sources.py` | `ChatSources`, workbook tool schemas, `CHAT_INSTRUCTIONS`, `compose_question` |
| `provenance/web/ledger.py` | Append-only spend ledger with cap |
| `provenance/web/worker.py` | Child-process turn runner, `StreamingTrace`, `summarize_event`, `TurnRunner` (parent side) |
| `provenance/web/replay_scripts.json` | Scripted replay turns (labeled) for tests and offline fallback |
| `provenance/web/app.py` | FastAPI app: config, sessions, sources, workbook, turns/SSE, exports, static files |
| `provenance/web/__main__.py` | `python -m provenance.web [--port 8765] [--replay] [--host 127.0.0.1]` |
| `scripts/make_demo_workbook.py` | Builds `data/demo/cloudflare-fy2024-model.xlsx` |
| `data/demo/cloudflare-fy2024-model.xlsx` | Committed fixture (Excel-saved, stable hash) |
| `tests/test_web_workbook.py`, `tests/test_web_chat_sources.py`, `tests/test_web_worker.py`, `tests/test_web_app.py` | Backend tests (unittest) |
| `web/` | Vite React app: `src/api.ts`, `src/types.ts`, `src/App.tsx`, `src/components/*`, `e2e/loop.spec.ts` |
| `package.json` (root) | Add `web`, `web:build`, `web:e2e` scripts |
| `README.md`, `context.md`, `roadmap.md` | Run instructions, verified status, M2/M5 status |

---

### Task 1: Dependencies, workbook snapshot and export

**Files:**
- Modify: `pyproject.toml` (add `fastapi`, `uvicorn`, `openpyxl`, `python-multipart` to `dependencies`), `uv.lock` (via `uv add`)
- Create: `provenance/web/__init__.py`, `provenance/web/workbook.py`, `scripts/make_demo_workbook.py`, `data/demo/cloudflare-fy2024-model.xlsx`
- Test: `tests/test_web_workbook.py`

**Interfaces:**
- Produces:
  - `class WorkbookError(ValueError)`
  - `parse_range(text: str) -> tuple[int, int, int, int]` → `(min_row, min_col, max_row, max_col)`; accepts `B5`, `A1:C3`, `$A$1`; raises `WorkbookError`.
  - `format_address(row: int, col: int) -> str`; `display(value) -> str` (None→"", bool→TRUE/FALSE, int→str, float→`f"{v:.10g}"`, date/datetime→ISO date, str→as-is).
  - `@dataclass class Snapshot: snapshot_id: str; sha256: str; filename: str; data: bytes; sheets: list[dict]; warnings: list[str]` with methods `cells(sheet: str, rng: str, limit: int) -> list[dict]` (each `{"address","display","formula"}`; `formula` is the formula text or `None`; raises `WorkbookError` if over `limit` or unknown sheet) and `grid(sheet: str, rows=60, cols=26) -> dict` (`{"sheet","max_row","max_col","rows": [[cell|None]]}`).
  - `load_snapshot(data: bytes, filename: str) -> Snapshot` — two openpyxl loads (`data_only=True` for displayed values, normal for formulas), `sheets = [{"name","max_row","max_col"}]`, warnings for charts/images/pivots.
  - `export_copy(snapshot: Snapshot, changes: list[dict], out_dir: Path, *, approved_at: str) -> Path` — `changes` items `{"sheet","cell","new_content","rationale","citations","old_display","old_formula","source_titles"}`; applies to a formula-preserving load, adds a comment per changed cell, appends sheet `Provenance log`, sets `wb.calculation.fullCalcOnLoad = True`, saves `<stem>-provenance-<n>.xlsx`, reloads and verifies every change; raises `WorkbookError` on mismatch.

- [ ] **Step 1: Add dependencies**

Run: `uv add fastapi uvicorn openpyxl python-multipart && uv sync --locked --extra benchmark-metrics`
Expected: lock updated; `uv run python -c "import fastapi, openpyxl, multipart"` exits 0.

- [ ] **Step 2: Build the demo fixture**

`scripts/make_demo_workbook.py` writes sheet `Model`: A1 `Cloudflare, Inc. (NET) — FY2024 operating model (demo)`, A2 `Demo workbook. Inputs below are analyst assumptions dated 2024-08-15, before Q3 results.`, header row 4 `Metric | Value | Unit | Note`, then:
- row 5 `Q3 2024 revenue (analyst estimate)` | 425.0 | `USD million` | `Analyst estimate`
- row 6 `Q4 2024 revenue (analyst assumption)` | 445.0 | `USD million` | `Analyst assumption`
- row 7 `FY2024 revenue (analyst assumption)` | 1650.0 | `USD million` | `Analyst assumption`
- row 8 `FY2024 non-GAAP operating income (analyst assumption)` | 215.0 | `USD million` | `Analyst assumption`
- row 9 `Implied FY2024 non-GAAP operating margin` | `=B8/B7` | `%` | `Formula`

and sheet `Notes` with one line explaining the file is a public-data demo. Then open and save it once in Excel:
Run: `uv run python scripts/make_demo_workbook.py data/demo/cloudflare-fy2024-model.xlsx && osascript -e 'tell application "Microsoft Excel"' -e 'open POSIX file "'$PWD'/data/demo/cloudflare-fy2024-model.xlsx"' -e 'save active workbook' -e 'close active workbook saving no' -e 'end tell'`
Expected: a `data_only=True` load shows B9 ≈ `0.1303030303`.

- [ ] **Step 3: Write failing tests** in `tests/test_web_workbook.py`:
  - `test_parse_range_variants`: `parse_range("B5") == (5,2,5,2)`, `parse_range("$A$1:C3") == (1,1,3,3)`; `"5B"`, `"A0"`, `"C3:A1"` raise `WorkbookError`.
  - `test_fixture_snapshot`: load fixture bytes → `snapshot_id == sha256[:12]`, sheets include `Model`; `cells("Model","B7:B9",200)` displays `["1650","215","0.1303030303"]` (B8 `"215"`) and B9 formula `"=B8/B7"`.
  - `test_rejects_non_xlsx`: `load_snapshot(b"not a zip", "x.xlsx")` and filename `x.xlsm` raise `WorkbookError`; > 5 MB raises.
  - `test_range_limit`: `cells("Model","A1:Z20",200)` raises (520 cells).
  - `test_export_applies_and_verifies`: export B7 → `1661.5` and B8 → `220.5` → reloaded copy has those values, B9 still `=B8/B7`, sheet `Provenance log` has header + 2 rows, B7 has a comment containing the source title; original `snapshot.data` hash unchanged.
  - `test_export_formula_change`: `new_content="=B7*0.13"` lands as formula text.

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_web_workbook -v`
Expected: FAIL (`ModuleNotFoundError: provenance.web.workbook`).

- [ ] **Step 5: Implement `provenance/web/workbook.py`** per Interfaces.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_web_workbook -v`
Expected: PASS (6 tests).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock provenance/web scripts/make_demo_workbook.py data/demo tests/test_web_workbook.py
git commit -m "feat(web): add workbook snapshots, demo fixture, and verified export"
```

### Task 2: ChatSources, chat instructions and context composition

**Files:**
- Create: `provenance/web/chat_sources.py`
- Test: `tests/test_web_chat_sources.py`

**Interfaces:**
- Consumes: `Snapshot`, `parse_range`, `format_address`, `WorkbookError` (Task 1); `Sources`, `function`, `TOOL_SCHEMAS`, `locator_range` (`provenance/sources.py`); `INSTRUCTIONS` (`provenance/model.py`).
- Produces:
  - `WORKBOOK_TOOL_SCHEMAS: list[dict]` — `read_workbook_range{sheet:string, range:string}` and `propose_cell_edit{sheet:string, cell:string, new_content:{"type":["number","string"]}, rationale:string, citations:{"type":"array","items":{object source_id/locator/quote, all required, additionalProperties false}}}`, both built with `function()`.
  - `CHAT_INSTRUCTIONS: str` = `INSTRUCTIONS + CHAT_ADDENDUM` (text below).
  - `class ChatSources(Sources)`: `__init__(directory, *, snapshot: Snapshot | None = None, preread_range: tuple[str, str] | None = None, **kwargs)`; attributes `proposals: list[dict]`, `tool_schemas` (base + workbook schemas when `snapshot`); overrides `call(name, args, timeout)` and `check_citation(citation)`.
  - `compose_question(question: str, *, corpus_label: str, cutoff: str, history: list[dict], snapshot: Snapshot | None, context: dict | None) -> str` where `history` items are `{"question","answer"(dict|None),"status"}` (last 3 used) and `context` is `{"sheet","range"}`.

`CHAT_ADDENDUM` (exact copy):

```text
Conversation and workbook rules for this chat:
- The user message may begin with a research context block and earlier turns. Earlier answers are not evidence: re-read any source lines you cite in this turn. Carried locators show where to read.
- If a workbook is attached, read_workbook_range returns cells from that immutable snapshot. Cite cells with source_id "workbook:<snapshot_id>", locator "Sheet!B5" or "Sheet!A1:C3", and a quote equal to a cell's displayed value or formula. Cells listed in the context block count as read.
- Workbook inputs are analyst assumptions unless the workbook says otherwise; never present them as reported facts.
- Use propose_cell_edit only when the user asks for changes or clearly asks whether an input should be updated. Each proposal needs a short rationale and citations to evidence you already read. Proposals are not applied: never say the workbook was changed; say the analyst can review and approve them.
```

- [ ] **Step 1: Write failing tests** in `tests/test_web_chat_sources.py` (corpus `data/cloudflare-2024-q3`, fixture snapshot):
  - `test_schemas_only_with_workbook`: `ChatSources(dir).tool_schemas == TOOL_SCHEMAS`; with snapshot, names are `search, read_source, read_workbook_range, propose_cell_edit`.
  - `test_read_workbook_range_marks_seen`: call returns `{"snapshot_id","sheet","range","cells":[...]}` and `seen["workbook:<id>"]` contains `"Model!B7"`; over-limit range returns `{"error": ...}` (not raises).
  - `test_workbook_citation_rules`: after reading `Model!B7`, citation `{"source_id":"workbook:<id>","locator":"Model!B7","quote":"1650"}` passes; quote `"1700"` raises `ValueError`; unread `Model!B8` raises; preread range `("Model","B8:B8")` makes B8 citable.
  - `test_corpus_citation_unchanged`: read `cloudflare-q3-2024-release` lines 59–64 via `call("read_source", …)`, citation quote `"Total revenue of $1,661.0 to $1,662.0 million"` with locator `L63` passes.
  - `test_propose_requires_read_evidence`: proposing B7 → 1661.5 with an unread release citation returns `{"error": ...}` and records nothing; after reading, it returns `{"proposal_id":"P1","status":"pending_human_approval",...}` and `proposals[0]` has `old_display == "1650"`, `old_formula is None`, `new_content == 1661.5`.
  - `test_propose_validation`: bad cell `"B0"`, unknown sheet, empty rationale, formula longer than 500 chars, 11th proposal → each returns `{"error": ...}`; a second proposal for the same cell replaces the first.
  - `test_compose_question`: output contains `"Evidence set: Cloudflare Q3 2024 packet"`, the cutoff, `"workbook:<id>"`, `"Model!B7 = 1650"` for context `B7:B7`, the last 3 of 4 history questions only, carried claim locators like `[cloudflare-q3-2024-release L63]`, and ends with `"Current question: <q>"`; with no history/workbook it contains neither section.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_web_chat_sources -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `provenance/web/chat_sources.py`** per Interfaces. `call()` dispatches workbook tools only when `snapshot` is set, returns `{"error": str}` for `ValueError`/`WorkbookError` like the base class; workbook reads add addresses (strings) to `self.seen[f"workbook:{id}"]` so `run_graph` checkpoint save/load preserves them; `check_citation()` handles `workbook:` IDs (cells must be in `seen` or the preread set; normalized quote must be contained in the joined display/formula text of the cited cells), else `super()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_web_chat_sources -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add provenance/web/chat_sources.py tests/test_web_chat_sources.py
git commit -m "feat(web): add workbook tools, cell citations, and chat context composition"
```

### Task 3: Spend ledger

**Files:**
- Create: `provenance/web/ledger.py`
- Test: `tests/test_web_worker.py` (ledger cases live here)

**Interfaces:**
- Produces: `class Ledger: __init__(path: Path, cap_usd: float)`; `total() -> float`; `remaining() -> float`; `turn_budget(max_turn: float = 0.10) -> float | None` (None when remaining < 0.01); `record(turn_id: str, cost_usd: float, *, uncertain: bool, model: str, mode: str, status: str) -> None` (append JSONL with ISO time; replay records cost 0 and is excluded from `total()`).

- [ ] **Step 1: Write failing tests** `test_ledger_caps_and_persists`: cap 0.20, record 0.15 live → `remaining()≈0.05`, `turn_budget()==0.05`; record 0.045 → `turn_budget() is None`; new `Ledger` on same path reads total `0.195`; replay records don't count.
- [ ] **Step 2: Run** `uv run python -m unittest tests.test_web_worker -v` → FAIL.
- [ ] **Step 3: Implement** `provenance/web/ledger.py`.
- [ ] **Step 4: Run** same command → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(web): add capped spend ledger"` (with the two files).

### Task 4: Turn worker and replay scripts

**Files:**
- Create: `provenance/web/worker.py`, `provenance/web/replay_scripts.json`
- Test: `tests/test_web_worker.py` (extend)

**Interfaces:**
- Consumes: `ChatSources`, `CHAT_INSTRUCTIONS`, `compose_question` (Task 2); `load_snapshot` (Task 1); `run_graph` (`provenance/graph.py`); `Limits`, `Trace` (`provenance/agent.py`); `OpenRouterModel` (`provenance/langchain_model.py`); `ReplayModel` (`provenance/model.py`).
- Produces:
  - `summarize_event(event: dict, started: float) -> dict | None` → `{"kind","label","detail","t","cost_usd"}`; kinds: `started`, `model` (model_response: number, tokens), `search` (tool_request search: query; tool_result: top 5 hits `{source_id, locator, title}` in `detail.hits`), `read` (read_source result: `source_id`, `title`, `locator`), `workbook_read`, `proposal`, `tool_error` (any result with `error`), `final_synthesis`, `answer_rejected` (reason), `finished` (status, reason). Other events → `None`.
  - `class StreamingTrace(Trace)`: `__init__(queue, log_dir=None, *, instructions: str, tools: list)`; `emit` appends normally, rewrites `run_started` `instructions`/`tools` to the given values, and puts `("event", summary)` when `summarize_event` returns non-None.
  - `run_turn_process(job: dict, queue) -> None` (child entry). `job` keys: `turn_id, question_text, corpus_dir, mode ("live"|"replay"), replay_responses (list|None), workbook_bytes (bytes|None), workbook_filename, preread (tuple|None), limits (dict), log_dir (str|None)`. Puts exactly one terminal message: `("done", {"report": {run_id, mode, status, stop_reason, answer, metrics, model}, "proposals": [...]})` or `("error", message)`.
  - `class TurnRunner` (parent): `start(job) -> Turn` where `Turn` has `id, events: list[dict], result: dict | None, error: str | None, done: threading.Event`; a reader thread drains the queue; if the child exits without a terminal message → error `worker_crashed`; if alive after `limits.timeout_seconds + 30` → terminate, error `worker_timeout`.
  - `load_replay_script(question: str, corpus: str, *, has_workbook: bool) -> list | None` (normalized whitespace/case match against `replay_scripts.json` entries `{question, corpus, needs_workbook, responses}`).

- [ ] **Step 1: Author `replay_scripts.json`** with two Cloudflare entries using real line numbers from `data/cloudflare-2024-q3`:
  1. "What revenue did Cloudflare report for Q3 2024, and what full-year 2024 revenue guidance did management give?" → search → read release lines covering L44–L64 → answer with claims `q3_2024_total_revenue` 430.1 USD million Q3 2024 and `fy2024_revenue_guidance_low/high` 1661.0/1662.0 USD million FY2024, quotes copied exactly.
  2. "Does the FY2024 revenue assumption in my model match management's latest guidance? If not, propose an update." (`needs_workbook: true`) → `read_workbook_range Model!A4:D9` → search → read release L59–L64 → `propose_cell_edit` B7 → 1661.5 citing L63 → answer citing `workbook:<fixture id> Model!B7` and L63.
- [ ] **Step 2: Write failing tests**:
  - `test_summarize_event_kinds`: synthetic events for each kind map to the documented `kind`; an unrelated event returns `None`.
  - `test_replay_turn_end_to_end`: `run_turn_process` in-process (plain `queue.Queue`) with script 1 → events include `search` and `read`; terminal `done` with `status == "completed"`, 2+ claims, `metrics.accounted_cost_usd == 0`, mode `offline_replay`.
  - `test_replay_workbook_turn_proposes`: script 2 with fixture bytes → `proposals[0]["cell"] == "B7"`, `new_content == 1661.5`, answer cites `workbook:<id>`.
  - `test_runner_reports_crash`: a job whose child raises before putting a terminal message (job `mode: "crash-test"` handled by raising `SystemExit(3)`) → `turn.error == "worker_crashed"` within 20 s, using the real spawn context.
  - `test_load_replay_script_match`: case/whitespace-insensitive match; workbook script not returned when `has_workbook=False`.
- [ ] **Step 3: Run** `uv run python -m unittest tests.test_web_worker -v` → FAIL.
- [ ] **Step 4: Implement `provenance/web/worker.py`.** Child builds `ChatSources(corpus_dir, snapshot=…, preread_range=…)`; live model `OpenRouterModel(key, model, in_rate, out_rate, max_output=4000, instructions=CHAT_INSTRUCTIONS, tool_schemas=sources.tool_schemas)`; replay `ReplayModel(responses)`; calls `run_graph(question_text, model, sources, Limits(**limits), trace)`.
- [ ] **Step 5: Run** same command → PASS.
- [ ] **Step 6: Commit** `git commit -m "feat(web): run chat turns in isolated worker processes with streamed events"`.

### Task 5: FastAPI app and CLI entry point

**Files:**
- Create: `provenance/web/app.py`, `provenance/web/__main__.py`
- Modify: `package.json` (scripts `"web": "npm --prefix web ci && npm --prefix web run build && uv run python -m provenance.web"`, `"web:build": "npm --prefix web run build"`, `"web:e2e": "npm --prefix web run e2e"`)
- Test: `tests/test_web_app.py`

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces `create_app(*, replay: bool = False, ledger_path: Path | None = None, cap_usd: float | None = None, runner: TurnRunner | None = None) -> FastAPI` and these routes (JSON unless noted; errors are `{"detail": str}`):
  - `GET /api/config` → `{"live_available": bool, "replay": bool, "model": str|null, "spend": {"total_usd","cap_usd","remaining_usd"}, "corpora": [{"id","label","cutoff","documents":[{"id","title","published","url","has_original"}],"starters":[str]}]}`. Corpus IDs `cloudflare-2024-q3` (label "Cloudflare Q3 2024 packet") and `earnings-excerpts` (label "Big Tech earnings excerpts"); cutoff = max `published`.
  - `POST /api/sessions {"corpus"}` → `Session`; `GET /api/sessions/{sid}` → `Session` = `{"id","corpus","turns":[TurnView],"workbook":WorkbookInfo|null,"context":{"sheet","range"}|null,"proposals":[Proposal],"exports":[Export]}`.
  - `GET /api/sources/{corpus}/{source_id}?start=&end=` (≤ 200 lines) → `{"id","title","url","published","total_lines","locator_note","has_original","lines":[{"line","text","location"}]}`; `GET …/original` → file (`application/pdf` or `text/html`), 404 when none.
  - `POST /api/sessions/{sid}/workbook` (multipart `file`) → `WorkbookInfo {"snapshot_id","filename","sha256","sheets","warnings"}`; marks existing proposals `stale`, clears context; 400 on invalid. `GET /api/sessions/{sid}/workbook/{sheet}` → `grid()`. `PUT /api/sessions/{sid}/context {"sheet","range"}` → `{"sheet","range","cells"}` (400 over 400 cells); `DELETE` clears.
  - `POST /api/sessions/{sid}/turns {"question","mode"}` → `{"turn_id"}`; 400 empty/over 4000 chars; 409 if a turn is running, if live is unavailable, or if the ledger refuses (detail names the cap); replay without a script → 404 `No scripted replay for this question`.
  - `GET /api/sessions/{sid}/turns/{tid}/events` → `text/event-stream`: `id: <n>` + `event: progress` per summary; final `event: done` with `TurnView`, or `event: error` with `{"message"}`; honors `Last-Event-ID`.
  - `TurnView = {"id","question","status","stop_reason","mode","model","answer","metrics","proposal_ids","carried":{"turns": int,"workbook_range": str|null}}`; `Proposal = {"id","turn_id","snapshot_id","sheet","cell","old_display","old_formula","new_content","rationale","citations","status"}` (status `pending|stale|exported`; `id = f"{turn_id}-{child proposal_id}"`, e.g. `t3-P1`, so IDs are unique per session).
  - `POST /api/sessions/{sid}/exports {"snapshot_id","proposal_ids"}` → `Export {"id","filename","snapshot_id","proposal_ids","changes","created_at","download_url"}`; idempotent on `(snapshot_id, sorted ids)`; 409 for stale/mismatched snapshot/unknown IDs. `GET /api/exports/{eid}/download` → `.xlsx` attachment.
  - Static: serves `web/dist` at `/` when present.
- `__main__`: loads `.env` (no override), `uvicorn.run(create_app(replay=args.replay), host, port)`.

- [ ] **Step 1: Write failing tests** with `fastapi.testclient.TestClient` and a temp ledger:
  - `test_config_lists_corpora_without_secrets`: two corpora, `starters` non-empty, response text contains no `OPENROUTER_API_KEY` value (set a fake env key in test).
  - `test_source_window`: release lines 59–64 returned with `has_original: true`; `end-start > 200` → 400; unknown source → 404.
  - `test_replay_turn_streams_and_completes`: create session, POST turn script 1 in replay mode, read SSE until `done`; progress events present; `TurnView.status == "completed"`.
  - `test_sse_resume_no_duplicates`: re-request events with `Last-Event-ID: 1` → first `id` received is `2`.
  - `test_workbook_flow_and_export_idempotent`: upload fixture, set context `Model!B7:B8`, run script 2, POST export twice → same `id`; download parses with openpyxl and B7 == 1661.5; original fixture hash unchanged.
  - `test_reupload_marks_stale`: after proposals, upload again → proposals `stale`; export → 409.
  - `test_rejections`: empty question 400; `.xlsm` upload 400; live turn with no key 409; second concurrent turn 409; ledger at cap → live 409.
- [ ] **Step 2: Run** `uv run python -m unittest tests.test_web_app -v` → FAIL.
- [ ] **Step 3: Implement** `app.py` and `__main__.py`.
- [ ] **Step 4: Run** `uv run python -m unittest tests.test_web_app -v` → PASS, then the full suite `corepack yarn test` → all pass (440 + new).
- [ ] **Step 5: Commit** `git commit -m "feat(web): add FastAPI chat, evidence, workbook, and export API"`.

### Task 6: Frontend shell, conversation and evidence

**Files:**
- Create: `web/package.json`, `web/index.html`, `web/vite.config.ts` (React + `@tailwindcss/vite`; dev proxy `/api` → `http://127.0.0.1:8765`), `web/tsconfig.json`, `web/src/main.tsx`, `web/src/index.css`, `web/src/types.ts`, `web/src/api.ts`, `web/src/App.tsx`, `web/src/components/{Header,Conversation,AnswerCard,Composer,Inspector,EvidencePanel,ActivityPanel}.tsx`
- Modify: `.gitignore` (add `web/node_modules/`, `web/dist/`, `web/test-results/`, `web/playwright-report/`)

**Interfaces:**
- Consumes: Task 5 routes and JSON shapes (mirror them in `types.ts`).
- Produces: `api.ts` functions `getConfig()`, `createSession(corpus)`, `getSession(id)`, `getSourceWindow(corpus, id, start, end)`, `startTurn(sid, question, mode)`, `streamTurn(sid, tid, onProgress, onDone, onError): () => void` (EventSource), `uploadWorkbook(sid, file)`, `getGrid(sid, sheet)`, `setContext(sid, sheet, range)`, `clearContext(sid)`, `createExport(sid, snapshotId, ids)`. App state: `selectedCitation: {sourceId, locator, quote} | null` and `inspectorTab: "evidence"|"activity"|"workbook"|"changes"`.

- [ ] **Step 1: Scaffold** with `npm create vite@latest web -- --template react-ts`, add `tailwindcss @tailwindcss/vite`, remove template assets.
- [ ] **Step 2: Implement** (load the `frontend-design:frontend-design` skill first): header (corpus selector with cutoff and documents, Live/Replay badge, spend meter, New conversation); conversation with starters, user bubbles, `AnswerCard` (answer text, claims table with value + unit + period, citation chips; abstention style; status/stop reason; metrics footer: model calls, tool calls, errors, tokens, cost, latency; "Scripted replay" label when `mode === "offline_replay"`); carried-context chip; composer (Enter sends, Shift+Enter newline, disabled while running); inspector tabs; `EvidencePanel` loads a window around the cited lines, highlights cited lines and the quote, shows title/date/URL/page-or-section, "Open original" (`/api/sources/.../original#page=N` for PDFs) and "Public source ↗"; `ActivityPanel` renders streamed progress rows live and final metrics.
- [ ] **Step 3: Verify** `npm --prefix web run build` exits 0 with no TypeScript errors; with `uv run python -m provenance.web --replay` running, `http://127.0.0.1:8765` loads and replay script 1 renders an answer whose chip opens the highlighted release lines (checked in browser).
- [ ] **Step 4: Commit** `git commit -m "feat(web): add chat interface with live activity and evidence viewer"`.

### Task 7: Workbook panel and changes/approval panel

**Files:**
- Create: `web/src/components/{WorkbookPanel,ChangesPanel,Grid}.tsx`
- Modify: `web/src/App.tsx`, `web/src/components/{Composer,AnswerCard,EvidencePanel}.tsx`

**Interfaces:**
- Consumes: Task 6 `api.ts`; Task 5 `WorkbookInfo`, `Proposal`, `Export`.
- Produces: workbook citation chips (`source_id` starting `workbook:`) open `WorkbookPanel` with the cited cells highlighted.

- [ ] **Step 1: Implement** upload (button + drag-drop, shows snapshot ID/hash/warnings and errors), sheet tabs, grid with row/column headers, click and shift-click range selection, "Use as context" / "Clear" (composer shows the attached range chip); `ChangesPanel` lists proposals (cell, old → new, rationale, citation chips, status), checkboxes (pending only), "Approve & generate copy" → export record with change list, "Download edited copy" link, and the note "Formulas recalculate when Excel opens the file; the app does not compute them." Stale proposals are visibly disabled with the reason. A badge on the Changes tab counts pending proposals.
- [ ] **Step 2: Verify** build passes; in replay mode the workbook script runs end to end in the browser and the downloaded file opens in Excel with B7 = 1661.5, a comment on B7, and the `Provenance log` sheet.
- [ ] **Step 3: Commit** `git commit -m "feat(web): add workbook context and approved-edit export UI"`.

### Task 8: End-to-end test, docs, and dogfood

**Files:**
- Create: `web/playwright.config.ts` (webServer `uv run python -m provenance.web --replay --port 8799` from repo root, with `WEB_LEDGER` pointing at a temp file), `web/e2e/loop.spec.ts`, `docs/dogfood/2026-11-17-web-mvp.md`
- Modify: `README.md` (Web MVP section: setup, `.env`, `corepack yarn web`, replay flag, limits), `context.md` (verified status), `roadmap.md` (M2/M5 state)

- [ ] **Step 1: Write `loop.spec.ts`** covering: config loads with Replay badge; ask script 1 → answer card with 430.1 and a chip; chip opens Evidence with highlighted line containing `$430.1 million`; upload the fixture → grid shows `1650`; select B7:B8 → context chip; ask script 2 → Changes badge 1; approve → download event yields a file whose name ends `.xlsx`; zero console errors.
- [ ] **Step 2: Run** `npx --prefix web playwright install chromium && corepack yarn web:e2e` → PASS.
- [ ] **Step 3: Update docs** and run `corepack yarn lint && corepack yarn test` → both pass.
- [ ] **Step 4: Commit** `git commit -m "test(web): add end-to-end replay loop and document the web MVP"`.
- [ ] **Step 5: Dogfood rounds 1–5** (live, ≤ $1 total): each round follows the design's loop and rubric, records score, defects, evidence screenshots, and spend in `docs/dogfood/2026-11-17-web-mvp.md`, fixes defects with tests where testable, and commits per fix. Stop iterating at 19:15 and record the final score.
