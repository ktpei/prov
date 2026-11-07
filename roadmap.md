# Finance agent roadmap

Draft modules · 2026-11-04

The current milestone is company-context research using polished `search` and
`read_source` tools, with evaluation. Workbook operations and workbook-aware
research move to the next milestone. The final product remains an Excel add-in;
standalone workbook export is not a required gate. Chatbot/UI and named-owner
planning are deferred. The modules below retain later architecture reference;
the sequence here supersedes their original ordering.

## Implementation update — 2026-11-07

First migration increment: LangChain/OpenRouter adapter and LangGraph execution
with model, tool, and finalize nodes, sharing existing evidence/trace/limit checks.
New page-text JSON ingestion builds immutable extracted-text packets with hashes
and line-to-page maps. Search ranks passages; reads expose page references and
continuation positions. See [ingestion.md](ingestion.md) for the actual contract.

Verified: all 44 tests pass in the project virtual environment, including actual
LangGraph replay and call-limit integration tests. Research dependencies are now
installed and recorded in pyproject.toml/uv.lock. Earlier package-installation
blockers below are historical. OpenRouter is configured locally with the selected
baseline model deepseek/deepseek-v4.1-flash-1017. Accounting currently uses provisional
$0.40/$1.60 per million input/output tokens, retained as estimates rather than
asserted DeepSeek provider prices; verify the selected route before live acceptance. Credentials remain in ignored local configuration, never in
tracked documentation. The user reports a $1/day limit configured in OpenRouter
(not independently verified). Keep development runs at $0.10 maximum each and
track costs; the application currently enforces per-run estimates, not a shared
daily ledger. No live request has run.

Raw PDF extraction, checkpoint resumption, server-safe deadlines, parser comparison,
original-file retention, qualitative claim schemas, and expanded evaluation remain
pending. No actual company PDF extraction or model-quality evaluation is claimed.

## Active sequence — 2026-11-07

1. Establish a complete mixed-format company packet and source manifest. Candidate:
   [Cloudflare 2024](source-packet.md). Verify extraction, dates, original locators,
   completeness, and permitted reuse before freezing benchmark material.
2. Polish search/read: passage-level results, bounded reads, table/header context,
   navigation through full documents, stable citations, explicit truncation and
   extraction failures. Compare retrieval against human-located evidence.
3. Add the intended OpenRouter access layer after model/rate/budget configuration.
   Migrate to the selected LangChain + LangGraph stack from the existing custom
   loop, starting with one agent and search/read. Preserve independent evidence
   and evaluation contracts. Recheck
   deadlines, accounting, traces, and provider compatibility if migrating.
4. Extend evaluation for full-document numerical and qualitative research, source
   disagreement, and missing evidence. Preserve the existing 10/15 split; new
   tasks need their own version and split. Report retrieval and answer failures
   separately with cost, latency, and human citation-support review.
5. Next milestone: workbook-aware research and selected workbook capabilities.
   Later: user-facing integration through the intended Excel add-in.

Exit check: real research questions over complete company documents produce
inspectable supported answers or appropriate abstentions, with reproducible
traces and reviewed evaluation outcomes. No browser UI or workbook export is
required for this milestone. This remains a narrower milestone than the sponsor's
full 5–7-tool brief.

## Ownership

| Workstream | Primary owner | Responsibility |
| --- | --- | --- |
| Chatbot | Person A, name pending | Agent loop, provider integration, research interface, answer and trace presentation |
| Tooling and evaluation | Person B, name pending | Source integrations, provenance outputs, workbook tools, source/task QA, scorer, experiment runner, human review, metrics and report |
| Shared | Both | Task selection, contract changes, failure review, final demo |

The main implementation handoff is the tool contract between the chatbot and
source/workbook integrations. Both owners review evidence quality and failures.
Revisit workload as full-document ingestion and the interface scope become clear.

## M0 — Scope and shared contracts

**State** — In discussion. Existing brief and runtime contracts are documented.

Agree the first company packet, representative questions, workbook support,
weekly capacity, model/spending constraints, and names for the two owners.
Confirm the answer/report contract between runtime and evaluation. Define how
qualitative claims and original page/table citations extend the numeric schema.

**Exit check** — Both owners can use one offline fixture as the agreed handoff.
Open decisions have owners and the first research questions are written down.

## M1 — Evaluation foundation and source packets

**Owner** — Person B, with Person A reviewing ingestion needs.

**State** — Five source extracts and 25 tasks exist. Full packets remain proposed.

- Validate the existing corpus and preserve the dev/heldout split.
- Select 2–3 companies and a historical reporting window.
- Curate releases, filings, and available presentations or call materials.
- Record original URLs, dates, hashes, extraction method, and useful locators.
- Define full-document development tasks with gold claims and review rubrics.
- Version additions separately and establish their heldout boundary.

**Exit check** — Another person can find each expected fact in the original
source, identify its period and units, and reproduce derived answers.

## M2 — Browser chatbot and backend API

**Owner** — Person A.

**State** — The Python agent loop, OpenAI adapter, and offline replay exist.
The browser interface and API are unimplemented. This module delivers the web app.

- Select and configure an exact model and budget when live calls are resumed.
- Run one development question and inspect tools, evidence, output, and charges.
- Build React + TypeScript + Vite chat with Tailwind CSS and a FastAPI backend.
- Show citations, source passages, tool progress, and run status in the browser.
- Define sessions, follow-up context, cancellation, and per-run state isolation.
- Adapt existing main-thread signal deadlines for API/server execution.
- Support the agreed research context and human-readable answer presentation.
- Add follow-up conversation only after defining carried evidence and cutoff.
- Keep automated evaluation callable directly against the Python backend.

**Exit check** — A user can ask a real development question in the browser,
see tool progress, inspect a cited answer and its supporting passage, and ask a
follow-up. API errors and limit stops appear in the UI and run report. Deadline,
cancellation, and session-isolation checks pass. Offline fixtures continue working.

## M3 — Financial source tools and evidence

**Owner** — Person B. Person A integrates the tool schemas and results into the chatbot.

**State** — Local search/read and contract-tested Exa adapters exist.

- Ingest the selected full documents and preserve page/table/section context.
- Verify live search separately from frozen-corpus evaluation.
- Add SEC filings/XBRL with fiscal period, unit, and filing identity.
- Preserve management guidance qualifications from prose and presentations.
- Make calculations traceable to their inputs.
- Add market data when a selected task requires it.
- Address Python isolation before exposing execution as a tool.

**Exit check** — Each added tool enables an agreed development task, returns
bounded output, preserves evidence identity, and reports recoverable errors.

M2 and M3 iterate together. Start with search/read before expanding toward the
sponsor's 5–7-tool target. Exact tool grouping remains a design decision.

## M4 — Evaluation runner and review

**Owner** — Person B.

**State** — Single-result mechanical pre-grading exists. Batch/reporting is pending.

- Consume existing result/trace artifacts before requesting runtime changes.
- Add repeatable dev runs and aggregate results with explicit denominators.
- Record model/configuration, corpus/task version, Git revision, and run IDs.
- Separate numeric correctness, citation validity, support, and abstention.
- Review derivations and unsupported additions using a consistent rubric.
- Track tool failures, stopped tasks, cost uncertainty, and latency.
- Keep a categorized failure log and feed dev findings back to Person A.

**Exit check** — One reviewed dev experiment has reproducible settings,
per-task outcomes, aggregate metrics, and explanations for failures.

M4 can start from offline fixtures while M2/M3 proceed. Scripted results remain
labeled as plumbing checks. They cannot establish model quality.

## M5 — Web MVP workbook exchange

**Owner** — Person A owns UI/API. Person B owns workbook tools and artifact checks.

**State** — Selected MVP path, unimplemented.

### M5a — Upload and context

Accept public `.xlsx` uploads as immutable identified snapshots. Provide a
sheet/range selector and table preview. Read bounded values, formulas, and labels
for research context. Bind cell citations to snapshot hash and sheet/address.
Require re-upload for desktop changes. Select supported features and input limits.

**Exit check** — Browser questions use the correct snapshot/range and labels.
Fixture values/formulas match originals. Sessions cannot mix workbook context.

### M5b — Approval and export

Preview exact changes with old/new values or formulas and sources. Bind approval
to the snapshot and proposal before generating a separate edited copy. Preserve
originals and include provenance/change information. Define retry behavior and
stale-proposal invalidation. Select and verify formula recalculation and support.

**Exit check** — Approved exports open correctly in Excel with intended changes,
source links, and supported formulas/formatting. Cached and verified results are
distinguishable. Failed exports never appear successful.

M5a can overlap browser research work. M5b follows verified reading and approval.
The demo expands to uploaded-range research, approved changes, download, and
reopening the edited workbook in Excel.

## M6 — Final evaluation and handoff

**Owner** — Person B leads evaluation. Both own delivery.

**State** — Pending research implementation and an agreed evaluation plan.

Freeze tasks, source snapshots, prompts, tools, model configuration, and scoring.
Agree success thresholds and human review before final runs. Run heldout tasks
only when authorized. Report benchmark limitations and any split contamination.
Prepare the one-command run path, three-minute demo, and one-page measurement
and failure report. Show browser chat, source inspection, workbook range context, and approved
export for completed increments. Include a source-to-answer example and actual
cost data. Live Excel integration has its own later demonstration.

**Exit check** — A reviewer can reproduce the run procedure, inspect evidence,
and distinguish verified behavior from future work.

## M7 — Later full Excel integration

**Owner** — Person A owns sidebar UI. Person B owns Office.js workbook tools and
host checks. Both agree the backend handoff.

**State** — Later phase after the web MVP.

Choose the primary host/API requirements. Add a manifest, HTTPS development setup,
and sideloading instructions. Reuse the research backend and suitable React UI.
Read live ranges/formulas and add approved in-place edits with stale-target
checks, duplicate prevention, and defined partial-write recovery. Verify selection,
writes, and recalculation in the real Excel host before broader model editing.

**Exit check** — Ask about a live range, inspect evidence, and approve a correct
edit. Changed target cells invalidate old approvals and recovery checks pass.

## First joint milestone

One question entered in the browser goes through retrieval, evidence reading,
answer generation, mechanical grading, and human review. Record citations,
trace, cost, latency, and review outcome.

The tooling/evaluation owner can prepare fixtures while the chatbot owner builds
the web shell. Real-model runs await model/budget selection. Source packets,
workbook support, thresholds, and dates remain open.
