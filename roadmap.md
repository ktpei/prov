# Finance agent roadmap

Module roadmap · updated 2026-11-07

The immediate workflow is company research through search/read tooling and an
independent evaluation runner. Workbook-aware research and Excel integration follow.
Read [spec.md](spec.md) for requirements and [context.md](context.md) for verification.

## Current milestone — company-context tooling and evaluation

Selected on 2026-11-07: LangChain + LangGraph, OpenRouter, and Cloudflare 2024
company documents. Deliver full-document ingestion, bounded passage search/read,
original evidence locations, checkpointed research execution, and separate
extraction/retrieval/answer evaluation. Native PDF/HTML extraction is the baseline;
Docling and Unlimited-OCR remain unselected challengers pending executable comparison.

Browser UI, workbook reading/writing/export, ownership allocation, and delivery
calendar questions are deferred. The eventual interface remains an Excel add-in.
The modules below retain the longer-term backlog; browser upload/download is no
longer the acceptance boundary of the current milestone.

Live acceptance uses the requested DeepSeek model with a $0.50 aggregate cap,
within the user-configured $1 daily limit. Keep heldout questions untouched.

## M0 — Scope and shared contracts

**State** — Current company-context scope and stack selected; broader product contracts remain a backlog.

Agree the first company packet, representative questions, workbook support,
weekly capacity, model/spending constraints, and names for the two owners.
Confirm the answer/report contract between runtime and evaluation. Define how
qualitative claims and original page/table citations extend the numeric schema.

**Exit check** — Both owners can use one offline fixture as the agreed handoff.
Open decisions have owners and the first research questions are written down.

## M1 — Evaluation foundation and source packets

**Owner** — Person B, with Person A reviewing ingestion needs.

**State** — Five source extracts and 25 tasks preserved; full four-document Cloudflare packet and nine development probes added.

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

**State** — LangChain/OpenRouter, LangGraph, checkpoints, and offline replay exist.
The browser interface and API are deferred. This module is a later interface backlog.

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

**State** — Full native HTML/PDF ingestion, page/section passages, bounded search/read,
and contract-tested Exa adapters exist. Native table/chart accuracy remains limited.

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

**State** — Frozen full-document retrieval diagnostics, per-answer pre-grading,
and explicit paid development batch execution exist. Semantic review and broader
independent evaluation remain necessary.

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

**State** — Deferred workbook-exchange option, unimplemented; not required for the active milestone.

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

**State** — First frozen development evaluation complete; broader final assessment
and human review remain pending. Six fresh public tasks were registered before
inference: 5/6 completed, 2/6 mechanical passes, 4/6 evidence-supported task passes
under coding-agent review. No runtime tuning or task reruns. See the
[report](eval/reports/frozen-evaluation-2026-11-07/report.md). Original holdout is
still unrun; single-company development results do not establish general accuracy.

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

**State** — Eventual product interface after research tooling and workbook-context validation.

Choose the primary host/API requirements. Add a manifest, HTTPS development setup,
and sideloading instructions. Reuse the research backend and suitable React UI.
Read live ranges/formulas and add approved in-place edits with stale-target
checks, duplicate prevention, and defined partial-write recovery. Verify selection,
writes, and recalculation in the real Excel host before broader model editing.

**Exit check** — Ask about a live range, inspect evidence, and approve a correct
edit. Changed target cells invalidate old approvals and recovery checks pass.

## Current acceptance checks

- A complete public company packet is reproducibly searchable with bounded evidence reads.
- One model chooses search/read, returns citations, and records cost/latency and limits.
- Checkpoint/resume preserves evidence and accounting without replaying completed work.
- Report extraction, retrieval, answer validity, and semantic-review limits separately.
- Existing 25-task dataset and offline checks remain valid; no heldout model tuning.
- Save exact setup, verified results, failures, and remaining work in the repository.
