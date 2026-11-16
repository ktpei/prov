# Web chatbot MVP — design

2026-11-17 · branch `feat/web-chatbot-mvp` (from `codex/finance-benchmark-loop`) · demo at 20:00 local

## Intent

Ship the browser MVP of the finance research agent for tonight's demo. An analyst
picks company evidence, asks a question, watches the agent research, and gets an
answer where every number links to the exact source passage it came from. They
ask follow-ups, bring their own `.xlsx` for context, and approve agent-proposed
cell edits that download as a separate edited copy carrying a provenance record.

This is the chatbot half of the two-person split in [roadmap.md](../roadmap.md)
(M2 browser chat + M5a/M5b workbook exchange). The research runtime, sources and
evaluation work on the base branch are consumed, not rewritten. The spec's first
research milestone is literally "ask a development question in the browser and
inspect its cited answer, source passages, and tool progress"; tonight extends
that to the full web MVP workflow in [spec.md](../spec.md#later-interface-workflow-and-demo).

## Decisions made by the user (2026-11-17)

| Topic | Decision |
| --- | --- |
| Scope | All four: cited chat core, follow-up questions, workbook upload + range context, approved edits + download |
| Evidence | Both, selectable in the UI: Cloudflare Q3 2024 packet (`data/cloudflare-2024-q3`, 4 full documents) and the 5-company excerpt corpus (`data/corpus`) |
| Live model | User provides `OPENROUTER_API_KEY`; model and rates per `.env.example` (`deepseek/deepseek-v4.1-flash-1017`, $0.30 / $1.20 per M tokens) |
| Spend | Up to $1.00 total for building + dogfooding live calls; the 20:00 demo gets its own fresh $0.25 allowance (separate ledger) so a spent cap cannot block it |
| Cut order | If time runs short, approved edits + download is cut or simplified first; everything else stays |
| Dogfood scoring | Builder scores each round with screenshot evidence; at 19:15 stop iterating and ship the best green state with its honest score |
| Stack | Per spec: React + TypeScript + Vite + Tailwind CSS frontend, Python + FastAPI backend |
| Base | Latest integrated branch; `feat/evaluation-agent-foundation` is superseded and not merged |

## Goals

1. One command starts the app locally (backend + built frontend on one port).
2. Ask a question against a selected evidence set; see live tool activity
   (searches, reads, model turns, running cost) while the agent works.
3. Answers show a claims table — metric, value, unit, period — where every claim
   has citation chips. A chip opens the evidence viewer at the cited lines with
   the quote highlighted, the source title/date and public URL, plus the original
   PDF page or section where the corpus records one (only the Cloudflare PDFs
   carry real page numbers; the excerpt corpus has neither). Cloudflare packet
   chips also open the archived original (PDFs at the cited page).
4. Follow-up questions in the same conversation use explicit carried context
   (prior questions, answers and cited locators), visible in the UI.
5. Upload a `.xlsx`, preview sheets as a grid, select a range, and ask questions
   that use it. The agent can cite workbook cells.
6. The agent proposes cell edits (old → new value/formula, rationale, sources).
   Nothing is written until the user approves. Approval generates a separate
   edited copy with a provenance log sheet; the original is never modified.
7. Every run shows model calls, tool calls, tool errors, tokens, cost and
   latency, and stopped/failed runs show their reason. Spend is capped and logged.
8. Existing CLI, evaluation and all 440 existing tests keep working.

## Non-goals

- Office.js / live Excel add-in (M7), auth, hosting/deployment, persistent chat
  storage across server restarts.
- Exa live web search (no key; stays off), Python execution, market data, or
  XBRL tools in chat.
- Changes to retrieval, extraction, benchmarks or evaluation; heldout tasks.
- A formula recalculation engine (see Workbook export).

## Anti-goals — failure even if it "works"

- A number shown without a checkable source, or a citation chip that does not
  open to text containing its quote.
- Scripted replay presented as live inference. Replay is always labeled.
- Any file written without explicit approval, or the uploaded original altered.
- An export reported as successful when a change is missing or the file is corrupt.
- Spend beyond the cap, or hidden failures/stops.
- Breaking the existing CLI, evaluation, lint or tests.

## Constraints

- **Deadlines use SIGALRM** (`controls.deadline`), which only works in a main
  thread. Each chat turn therefore runs in a spawned child process whose main
  thread calls `run_graph`; events stream back over a multiprocessing queue.
  This also isolates per-turn evidence, budget and workbook-tool state.
- **Answer contract is exact-field** (`answerable`, `answer`, `claims`) and stays
  unchanged. Edit proposals travel through a tool, not the answer contract.
- **Citations must cite lines read in the same run** (`sources.seen` resets per
  run). Follow-ups re-read evidence; carried locators let the model go straight
  to them.
- **Spend**: per-turn budget $0.10 via `Limits.budget_usd`; a server-side ledger
  (`runs/web/cost-log.jsonl`) refuses live turns once the $1.00 total is reached
  (`WEB_SPEND_CAP_USD`, default 1.00; `WEB_LEDGER` selects the ledger file so the demo uses a fresh one). Uncertain charges are recorded as such.
  Default per-turn limits: 8 model calls, 10 tool calls, 120 s.
- Repo conventions (AGENTS.md): small commits, no AI attribution lines, keep
  README/context/roadmap current, `yarn lint` and `yarn test` pass. Public data only.

## Architecture

### Backend — `provenance/web/` (FastAPI, new; base code untouched)

- **Turn worker**: spawned process builds `ChatSources` + `OpenRouterModel`
  (or `ReplayModel` for replay) with chat instructions and extended tool schemas,
  calls `run_graph` with a `StreamingTrace` (subclass of `Trace` whose `emit`
  also enqueues the event), then sends the final report and proposals.
- **`ChatSources(Sources)`** adds two tools when a workbook snapshot is attached:
  - `read_workbook_range(sheet, range)` — ≤ 200 cells; returns address, display
    value, formula text (if any) and whether the value is a cached formula result.
  - `propose_cell_edit(sheet, cell, new_value | new_formula, rationale, citations)`
    — validates the target address and that each evidence citation passes
    `check_citation` (so evidence must already be read); records old value and
    formula; returns `pending_human_approval`. It writes nothing.
  - `check_citation` accepts `source_id = "workbook:<snapshot_id>"` with locator
    `Sheet!B5` or `Sheet!A1:C3`; cells must have been read; the quote must match
    a cell's display value or formula. All other citations defer to the base class.
- **Instructions**: base `INSTRUCTIONS` plus a chat addendum covering conversation
  context, workbook use, workbook citations and proposal rules (propose only
  when asked or clearly implied; cite the evidence; never claim the file changed).
- **Bookkeeping inside `run_graph`** (builder check): `run_graph` keeps only
  `documents` with `text_file` and reloads `seen` at every node, so workbook reads
  are recorded in `seen["workbook:<id>"]` as cell addresses, and proposals live on
  the `ChatSources` object. `StreamingTrace` rewrites the `run_started` event's
  `instructions`/`tools` to the chat values actually sent. The selected range is
  always in the user message, so context projection cannot drop it; workbook
  tool outputs stay small.
- **Replay** is labeled everywhere and used for automated tests plus one scripted
  offline walkthrough (Cloudflare guidance question → workbook proposal → export),
  enabled with `--replay` as a demo fallback. Unscripted questions in replay mode
  get a clear "no script for this question" message.
- **Dependencies added**: `fastapi`, `uvicorn`, `openpyxl`, `python-multipart`.
- **Sessions** (in memory): evidence set, turns, workbook snapshot and selected
  range, proposals, exports.
- **API** (JSON; progress over Server-Sent Events):
  `GET /api/config` · `POST /api/sessions` · `GET /api/sources/{corpus}/{id}?start&end`
  · `GET /api/sources/{corpus}/{id}/original` · `POST /api/sessions/{sid}/workbook`
  · `GET /api/sessions/{sid}/workbook/{sheet}` · `PUT /api/sessions/{sid}/context`
  · `POST /api/sessions/{sid}/turns` · `GET /api/sessions/{sid}/turns/{tid}/events`
  · `POST /api/sessions/{sid}/exports` · `GET /api/exports/{eid}/download`.

### Follow-ups

Each turn is a new `run_graph` call whose user message contains an explicit
context block: evidence set and cutoff, workbook snapshot ID and selected range
(cells inline, ≤ 400), and the last three turns (question, answer text, claims
with source/locator). Then the new question. The UI shows what was carried.

### Workbook

- `.xlsx` only, ≤ 5 MB, ≤ 30 sheets. `.xlsm`/`.xls`/invalid files are rejected
  with a clear message. Charts, images and pivots trigger a warning that the
  export copy will not keep them (openpyxl limitation).
- Snapshot ID = first 12 hex chars of the file's SHA-256; the original bytes are
  kept immutable. Values come from a `data_only=True` load (cached results) and
  formulas from a normal load. Uploading a new workbook invalidates prior proposals.
- Preview: sheet tabs and a grid (first 60 rows × 26 columns), click/shift-click
  range selection, "use as context" (≤ 400 cells).
- Export: apply the approved subset to a copy, add a cell comment with the source
  on each changed cell, append a `Provenance log` sheet (cell, old, new, rationale,
  source title/URL/locator/quote, snapshot hash, approval time), and set Excel
  to recalculate on open. Formula results in the copy are not computed by the
  app and are labeled "recalculated by Excel on open". The export is reloaded and
  every approved change verified before it is offered; failure returns an error.
  Repeated approval of the same snapshot + proposal set returns the same file.

### Frontend — `web/` (Vite + React + TS + Tailwind)

- **Header**: evidence set selector with cutoff and document list, Live/Replay
  badge, spend meter (session and total vs cap), new conversation.
- **Conversation**: starter questions per evidence set, user turns, answer cards
  (answer text, claims table with citation chips, abstention styling, status and
  metrics footer), "carried context" chip on follow-ups, composer showing the
  attached workbook range.
- **Inspector** tabs: Evidence (viewer above), Activity (streamed timeline, final
  metrics, stop reason), Workbook (upload, sheet grid, range selection),
  Changes (proposals table with checkboxes, approve → generate copy → download,
  and the provenance summary).

### Demo fixture

`data/demo/cloudflare-fy2024-model.xlsx`: a small analyst model built from public
packet figures, with an FY2024 revenue assumption labeled as a pre-Q3 analyst
input that differs from the Q3 release guidance ($1,661.0–1,662.0M). The demo
question asks whether the assumption matches the latest guidance; the agent
cites the release and proposes an update. A script builds it, then it is opened
and saved once in Microsoft Excel so formula cells carry cached values. The
committed binary is the fixture, so its snapshot hash stays stable.

Starter and dogfood questions use Cloudflare, Apple, NVIDIA and Meta only.
Amazon and Microsoft are reserved validation issuers (AGENTS.md) and stay out
of development tuning, though users can still ask about them.

## Testing

- Python unittest (repo convention): workbook load/range/export round trip and
  verification, `ChatSources` tool validation and workbook citations, context
  composition, spend ledger cap, and a full turn through FastAPI's test client
  with `ReplayModel` (SSE events, answer, proposals, export).
- Frontend: TypeScript typecheck and production build; Playwright end-to-end
  test of the full user loop in replay mode (no spend).
- The existing suite (440 tests) and `yarn lint` stay green.

## Dogfood loop — 5 rounds, bar 99/100

Each round drives the complete user loop in a real browser against the live
model: start app → ask a Cloudflare question → inspect citations → follow-up →
excerpt-corpus comparison question → unanswerable question → upload the demo
workbook → select range → ask the guidance question → review proposals → approve
→ download → open the copy in Microsoft Excel and check changes and provenance.
Each round is scored, the defects fixed, and the score recorded with evidence.
The bar: the final round scores ≥ 99 with zero anti-goal violations.
Estimated spend ≈ $0.10 per round.

| Area | Points |
| --- | --- |
| Launch: one command, config shows live mode, model, cap | 5 |
| Answer correctness: values, units, periods match sources; correct abstention | 20 |
| Citation integrity: every claim chip opens exact lines with quote highlighted; original link works | 15 |
| Live transparency: streamed activity, metrics, stop reasons, replay labeling | 10 |
| Follow-up: uses carried context correctly, carried context visible | 10 |
| Workbook upload and range context, including cell citations | 10 |
| Proposals, approval, export: nothing written before approval; copy opens in Excel with changes + log; original untouched; retry idempotent | 15 |
| Robustness: bad file, empty question, provider error, cap reached → clear messages | 5 |
| UX polish and accessibility: layout, readability, keyboard use, no console errors | 10 |

## Left to the builder

Component structure, visual design details, SSE event shapes, package manager
inside `web/`, exact limit values beyond those stated, starter question wording,
and fixture layout beyond the stated guidance comparison.
