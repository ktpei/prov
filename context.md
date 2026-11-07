# Working context — 2026-11-07

## Local handoff verification — 2026-11-07

Imported the verified Git bundle at `3643af7` into the local
`feat/company-research-end-to-end` branch. The earlier local implementation remains
on `feat/evaluation-agent-foundation` at `f37c4ba`; it was not overwritten or merged.
Local `yarn lint` and `yarn test` pass, with all 79 tests running. Python 3.13
reports unclosed SQLite connection ResourceWarnings during tests; passing checks
do not establish that connection cleanup is complete. No new paid calls were made.

## Active authorization

Build company-context research tooling and evaluation first. The user selected
LangChain + LangGraph with OpenRouter. Workbook capabilities, browser UI, ownership
questions, and export are deferred; workbook-aware research is the next milestone,
and the eventual product is an Excel add-in.

The user approved parallel development subagents (runtime, ingestion, evaluation)
and a $0.50 aggregate live-call cap within their $1 daily OpenRouter limit. Exact
requested model: `deepseek/deepseek-v4.1-flash-1017`. Never put credentials in code,
reports, or Git. Public-web discovery/Exa and GPU-backed OCR are not prerequisites.

## Checkout and continuity

The user supplied `https://github.com/ktpei/prov/tree/feat/evaluation-agent-foundation`.
Fetched commit `968068f` and created `feat/company-research-end-to-end` for changes.
That remote contained the 33-test custom-loop foundation plus planning documents;
it did not contain the previously described LangGraph/ingestion implementation.
This run rebuilds those capabilities against the available remote rather than
claiming that the earlier local implementation was recovered.

Git branch writes and network access work in this environment. PyPI installation,
provider access, and document download are checked during implementation; old
session permission/network failures are not current verification results.

## Evidence and architecture

Use a dated Cloudflare 2024 packet: earnings release, filing, call transcript,
and investor slides where accessible. Preserve originals, content hashes, source
URLs, page/section locations, table rows/headers/footnotes, and bounded tool output.
Stored company evidence, workflow/checkpoint state, and each model request are
separate. Search and read remain framework-independent. Native extraction is the
initial baseline; Docling and Unlimited-OCR remain unmeasured candidates.

The product uses a single model-directed research agent, with deterministic
limits, citation checks, accounting, and checkpoint boundaries. Development
subagents are an implementation aid, not a change to the selected sponsor brief.

## Evaluation discipline

Preserve the original 25-task corpus (10 development, 15 heldout), fake-provider
tests, and clearly labeled scripted offline replay. Add separately versioned
full-document tasks. Keep gold facts out of agent context. Report extraction,
retrieval, mechanical answer checks, and semantic support separately. A quote
match or replay pass does not establish model accuracy. No heldout model tuning
or final heldout experiment is authorized by this development task.

## Verification status

Baseline: all 33 existing offline tests passed before implementation. The `yarn`
executable was initially unavailable; Corepack provides Yarn 1.22.22. The public
OpenRouter model catalog lists the exact requested model with tools and structured
output support. Published prompt/output rates vary by schedule; live accounting
uses conservative maximum published rates and reports measured usage separately.

## Completed implementation and verification

- Dependencies installed/locked; SDK execution verified, with no skipped SDK tests.
- LangChain/OpenRouter adapter and LangGraph model/tool/answer runtime. Local
  SQLite supports safe tool-boundary pause/resume, stable cached completion, and
  durable pre-request markers blocking duplicate paid attempts after a crash.
- Runtime policy `research-v2-finalization` binds checkpoint identity. It reserves
  the last permitted model turn for tool-disabled synthesis or abstention, and
  supports one bounded final citation repair within existing limits.
- Native HTML/PDF ingestion stores independently hashed originals/text, line-to-page
  or section maps, bounded reads/continuation, and explicit extraction limitations.
- Complete Cloudflare release, 10-Q, 18-page transcript, and 116-page investor deck.
  Visual spot checks found useful values but unsafe stacked-chart text geometry.
- BM25/query-focused snippets default (`bm25-v2`); earlier passage ranking remains
  available (`passage-v1`) so old search/read traces can be regraded faithfully.
- Model context projection bounds serialized tool-result strings to 32K characters;
  complete canonical evidence and quote-read state remain outside model context.
- Nine frozen development probes; extraction anchors 8/8, retrieval 5/8 → 6/8. The
  original 25 tasks and heldout boundary remain intact.
- `corepack yarn lint` passed and `corepack yarn test` passed **79 tests**.
- 28 live development runs across five transparent iterations: total conservative
  token-rate accounting **$0.3498927**, below the approved $0.50 total. No uncertain
  billing flags, paid Exa, GPU, or OCR calls. All use the exact requested model.
- Nine-task BM25 batch: 5 completed, 3 mechanical passes. Subsequent targeted four-case
  finalization batch: 4 completed, 3 mechanical passes. Do not combine into 9/9 success.
- Coding-agent semantic review flags precision/source overconstraints in grading,
  genuine requested-source mismatches, incomplete header context, and uncited
  numerical prose in otherwise supported answers/abstentions. Human review pending.

See `eval/reports/live-acceptance.md` and raw traces/reviews for exact results.
The next work is semantic/citation completeness, new uninspected evaluation,
and parser/OCR comparison before expanding to workbook operations.

## Delivery and access

Implementation is committed on `feat/company-research-end-to-end`. GitHub push
failed with missing HTTPS credentials; neither GH_TOKEN nor GITHUB_TOKEN is
configured. The remote has not been updated. A full Git bundle is prepared for
local import. No new user decision is needed for offline use; GitHub authentication
is needed only to publish this branch directly from the execution environment.
The API key was used for approved requests, never written into repository files.
