# Working context — 2026-11-07

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

## Latest decisions — 2026-11-07

Tooling and evaluation first: company-context research across complete public
filings, releases, investor presentations, and call materials. Only polish search
and read for now. Supported qualitative answer scope is left to implementation
judgment. Workbook-aware research and workbook capabilities are deferred to the
next milestone, with the Excel add-in as the final interface. Standalone workbook
upload/download is no longer a required delivery gate. Chatbot implementation,
named ownership, and scheduling are not current blockers.

The user plans to provide OpenRouter access. LangChain + LangGraph are now
selected for the target architecture. Exact model and live-call budget/rates
remain pending; no new live call was made. Repository code
still uses the custom loop and direct OpenAI adapter, without any agent SDK.
Migration should preserve limits, trace/evaluation contracts, and citation checks.
Keep extraction providers replaceable; Unlimited-OCR and Docling remain candidates
requiring a finance-document extraction comparison. Neither is adopted. See source-packet.md
for verified public links and unverified ingestion/reuse boundaries. The original
25-task split remains untouched. Earlier sections below are historical and are
superseded by these decisions when they conflict.

## User request and constraints

Implement roadmap steps 1–2 of the first ProvenanceXL project brief. Ask when a
decision needs input. User chose: **OpenAI first; configure live calls later**.
Live calls remain deferred. Work is an informal unpaid side project.

The 2026-11-04 request adds a thorough draft specification, relevant project
context, a loose module roadmap, and decision questions. The user selected
research answers from company data as the first workflow. The corrected
two-person split is chatbot versus tooling and evaluation. The selected MVP is a browser app
with workbook upload/download, followed by full live Excel integration. The user wants a clearer account of realistic data, including investor
slides and numbers in comps workbooks. See [spec.md](spec.md) and
[roadmap.md](roadmap.md).

## Confirmed project context

On 2026-11-03 the user confirmed that the first brief in the
[Provenance × Tech@NYU artifact](https://claude.ai/artifact/3cSNqEgPBvGGNVjAj2vjcH)
is our project. The artifact was read directly in Chrome. `project.md` now
records the selected finance harness brief, the separate deal-agent brief,
alternative project ideas, shared ground rules, and semester deliverables.

Keep the distinction between the full sponsor ask (5–7 tools and a measured
25-task evaluation) and the implemented steps 1–2 (two read-only tools and
no live model evaluation yet). Planning for the wider brief is now authorized. Briefs 2–3 supply context, not authorization to
build a specialist-agent team or expand scope. Preserve the existing OpenAI-first,
live-calls-deferred decision.

## Current state

- Initialized Git from a directory containing only `AGENTS.md`; work is on
  `feat/evaluation-agent-foundation`. Remote `origin` points to
  `https://github.com/ktpei/prov`.
- Five official historical earnings-source extracts and a hash manifest.
- 25 tasks with gold claims and rubrics: 10 dev, 15 heldout; 3 unanswerable.
- Read-only model loop, two tools, OpenAI and optional Exa HTTP adapters,
  conservative budget accounting, limits, traces, and structured answers.
- Offline demo is a hand-authored replay, clearly labeled in output and docs.
- The documentation task re-ran all 33 offline tests successfully. Lint and
  dataset validation passed with `UV_CACHE_DIR=/tmp/prov-spec-uv-cache yarn lint`;
  the default uv cache path was inaccessible in this session.

## Verification boundary

Corpus data was verified against official public documents and statically
checked. Offline runtime tests cover control flow and failure paths. Live
OpenAI/Exa requests and model-quality evaluations remain unverified and deferred
by user choice. No heldout model evaluation has been run.

## Next authorized decision

When the user resumes live setup, choose an exact model, verify current pricing,
configure the rates and per-run budget, then run one development question and
review its trace before any broader evaluation. Preserve the heldout split.
An OpenAI key was present in the environment during inspection; its value was
not exposed, printed, or used in requests. Exa was not configured. Re-check
availability when needed.

## Proposed next planning decisions

- Select companies, reporting window, and representative questions. A proposed
  packet contains releases, filings, and available decks or call materials.
- Decide curated full-document packets versus live discovery. Preserve the
  existing excerpt benchmark as a regression set with its limitations.
- Define workbook feature support and recalculation for upload/download.
  Select a host for later Office.js integration.
- Assign named owners, weekly capacity, delivery dates, spending, and final
  evaluation thresholds.

The draft distinguishes original evidence, workbook context, derived values,
and analyst assumptions. It preserves the current numeric answer contract and
marks qualitative claims, richer provenance, and conversation support as future
extensions requiring coordinated runtime and evaluator work.

## Repository write limitation

During this documentation task, creating a feature branch failed because Git
could not create its ref directory under `.git`. The active filesystem profile
grants read access to `.git`. The draft files can be edited, but branch creation,
commits, and a PR remain blocked in this session.

## Latest push status

The temporary cloud workspace reconstructed these plans and created commit
`9428413` on `docs/web-mvp-spec-roadmap`. Automatic review blocked its push.
The user explicitly approved pushing afterward. The returned local environment
contains the earlier drafts and lacks that commit. Those drafts have now been
updated to the same agreed browser MVP and later live Excel direction. Local
branch creation still fails because `.git` is read-only in this environment.

The proposed stack is React + TypeScript + Vite, Tailwind CSS, and Python +
FastAPI. The browser demo includes citations, evidence inspection, and uploaded
range context, followed by approved exports. Workbook snapshots, source-to-cell
provenance, recalculation checks, and later Office.js integration are documented.
