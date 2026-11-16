# Working context — 2026-11-16

## Broader assessment preparation — 2026-11-16

The [locked native-HTML assessment plan](eval/assessments/native-html-v1/plan.md)
records a metadata-verified six-filing proposal across three new issuers, with 21
positive question slots and three publication-availability controls. Documents
are not yet acquired and questions are not authored. A separate search-only runner
passes synthetic integrity/interruption checks; annotation grading and cutoff
enforcement remain prerequisites.
Synthetic review found hidden-text and block-boundary defects in legacy HTML text
extraction; sidecar v2 guarantees do not apply to that path. Frozen corpora remain
unchanged. This is preparation, not a new accuracy result.


## Raw table runtime — 2026-11-16

[Fixed offline probe](eval/reports/table-runtime-2026-11-16/report.md): standalone
raw-table reads cover all required cells for 4/4 explicit-window controls, while
original-question search plus one read improves 1/4 → 2/4 after excluding redundant
prefix rows. Correct tables rank first 3/4 and within three 4/4. The raw grader does not infer semantic or typed answer success.
Default graph/citations remain unchanged; no additional paid inference occurred.
A frozen soft-prefix weighting challenger remained 2/4, with no paired wins or
losses. Both earlier versions replay exactly; v2 remains the default. The negative
result is retained, and broader uninspected development assessment is next.


## Source-quality iteration — 2026-11-16

Whole-document diagnostics bind originals, extracted text, and the full manifest.
Three-task retrieval reaches 2/4 annotated pages at five hits; declared-document
scoping improves first-hit recall from 1/4 to 2/4 without fixing the remaining task.
Native HTML v2 fixes explicit-hidden contamination and retains raw headers/captions;
four evaluator-only packets check source/period/sign/scale associations. Lint and
218 tests pass. Full-agent FinanceBench inference and human adjudication remain
pending. [Source findings](eval/reports/source-ingestion-2026-11-16/report.md).


## Expansion pilot — 2026-11-16

[Fixed table/conversation pilot](eval/reports/expansion-pilot-2026-11-16/report.md):
TAT-QA EM/F1/scale 4/4; both ConvFinQA history conditions 6/9 turns and 0/2 whole
conversations. All 22 requests completed; $0.0290532 conservative cost. Remaining
authorization $0.5185807. Source-level review flags annotation/scale ambiguities;
these small public development results are not human-validated financial accuracy.

## Table/conversation expansion — 2026-11-16

All five selected public dataset families now have adapters. TAT-QA uses a pinned
MIT-licensed official metric with explicit numeric-output safeguards; ConvFinQA
has history-isolated projections and per-turn/whole-conversation scoring, with
bounded conversation execution now available. New report-level partitions share FinQA/
ConvFinQA exposure rules. Full imports and 161 tests passed; no new model-quality
claim or spending accompanies this expansion. [Details](eval/external-benchmarks.md).

## External pilot measured — 2026-11-16

[Ten-task development pilot](eval/reports/external-pilot-2026-11-16/report.md):
CFA-Easy 3/3 and CFA-Challenge 2/2 adapted choice passes; FinQA 2/3 adapted scalar
passes with one output-limit failure; FinanceBench two completed oracle responses,
automatic semantic accuracy unset. Independent coding-agent review found an
underspecified FinQA question and FinanceBench denominator/percentage ambiguities.
These are tiny public development diagnostics, not official or human-validated scores.

At that pilot boundary, conservative cost was $0.0161622 and cumulative recorded
estimate $0.4523661. The later expansion pilot above supersedes its remaining budget. No uncertain billing flags or original
holdout calls. Implementation and protocol are published in draft
[PR #2](https://github.com/ktpei/prov/pull/2), not merged. Lint and 112 tests passed.
Earlier no-live-run statements below describe pre-pilot stages.

## Active benchmark loop — 2026-11-16

The user authorized continuous benchmark integration, extensive ingestion research,
and coordinated subagent work. [Workflow](eval/external-benchmarks.md),
[research](eval/external-benchmark-research.md), and [cycle ledger](eval/improvement-loop.md)
record current work. Five dataset families have adapters, hash-pinned preparation,
and bounded execution for tool-free conditions. Two preregistered pilots are
complete. Unresolved annotations are content-bound and retained in the denominator
for later preparations; old scores remain frozen. Source-quality diagnostics and
connected table-evidence acceptance are in progress. No human validation is claimed.

## Selected finance accuracy benchmarks — 2026-11-16

The user selected the comprehensive suite discussed in planning and requested it
be recorded for future implementation. Canonical plan:
[Finance accuracy benchmark plan](eval/benchmark-plan.md).

- Core first: Salesforce FinEval CFA subsets, FinQA, FinanceBench, and custom prov tasks.
- Next: TAT-QA for report-table interpretation and ConvFinQA for conversations.
- Later challenge: Finance Agent Benchmark when tools/source coverage support it.
- Excel/workbook benchmarking is explicitly deferred. Financial knowledge and
  evidence-backed research accuracy take priority over workbook-aware research.
- Separate model-only, correct-evidence-supplied, and full-agent conditions where
  applicable. Keep benchmark scores, citation support, and runtime compliance distinct.
- Initial targets: 100 FinEval, 100 FinQA, 100 TAT-QA questions, all 150 public
  FinanceBench examples across declared partitions, 30 ConvFinQA conversations,
  and 50 custom tasks. These are planning targets, not completed runs or guarantees.
- Preserve the original 25-task corpus and untouched 15-task holdout. Verify data
  licensing, versions, leakage boundaries, grader calibration, and execution budgets.

This update records a decision only. It does not install adapters, download data,
run inference, select an eval platform, or authorize additional spending. Historical
verification and authorization below remain dated records, not new measurements.

## Evaluation milestone — measured development baseline

The user selected evaluation as the next goal. Runtime baseline `d9057ed` remained
frozen. Six fresh public development questions and the protocol were committed
before inference at `ce1a2f2`; all six ran once with no tuning or reruns. Results:
5/6 final answers, 2/6 unchanged mechanical passes, and 4/6 evidence-supported task
passes under separate coding-agent review plus lead verification. This is not
general accuracy or human financial validation. Two numerical answers fail only
exact period strings; one otherwise passing answer adds a supported 2023 figure
outside structured claims. One task stops after a rejected table quote and a
reservation-blocked repair; one correct abstention never reads a source.

The report, protocol, raw traces, and per-task review are under
`eval/reports/frozen-evaluation-2026-11-07/`. Fresh extraction anchors pass 5/5;
fixed-query retrieval passes 4/5 positive tasks. Existing retrieval reproduces
6/8 and all 28 historical mechanical flags reproduce offline. Original heldout
inference remains unrun. No runtime, dependency, corpus, or original benchmark
changes were mixed into this evaluation.

Fresh estimated cost is $0.0863112, combined total $0.4362039 under the original
$0.50 authorization. Conservative current endpoint maxima $0.60/$2.40 per million
input/output tokens were used; prior cloud estimates used $0.30/$1.20. No uncertain
cost flags. Estimates are not provider invoices. No further paid trials were run.
Next work: synthesis/repair budget headroom, read-evidence discipline for abstention,
versioned period grading, narrative/claim completeness, then new multi-company
cross-source questions and human review. Do not tune and rescore this inspected
six-task batch as if it were still fresh.

## Local handoff verification — 2026-11-07

Imported the verified Git bundle at `3643af7` into the local
`feat/company-research-end-to-end` branch. The earlier local implementation remains
on `feat/evaluation-agent-foundation` at `f37c4ba`; it was not overwritten or merged.
Local `yarn lint` and `yarn test` pass, with all 79 tests running. Python 3.13
reports unclosed SQLite connection ResourceWarnings during tests; passing checks
do not establish that connection cleanup is complete. No new paid calls were made.

## Active authorization

After the frozen batch finished, the user answered the pending budget question
with “Authorize $0.50 additional.” Total authorized estimated development/evaluation
spending is now $1.00, with $0.4362039 accounted and $0.5637961 remaining. This
does not retroactively change the frozen batch's $0.15 cap, original protocol,
results, or rate assumptions. No additional paid calls accompanied this approval.
Continue to respect the reported account-side $1/day limit and verify actual
account usage before a future paid batch; application estimates are not invoices.

Build company-context research tooling and evaluation first. The user selected
LangChain + LangGraph with OpenRouter. Workbook capabilities, browser UI, ownership
questions, and export are deferred; finance accuracy benchmarking is the next planning priority,
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

Implementation was imported from the cloud bundle and pushed from this Mac on
`feat/company-research-end-to-end` at `d9057ed`. The earlier cloud push failure
was resolved by local import and authenticated push. Evaluation work uses
`codex/evaluation-baseline`, now pushed with measured results. Draft
[PR #1](https://github.com/ktpei/prov/pull/1) targets `main` and includes the
company-research implementation plus evaluation baseline; it is not merged.
Local GitHub authentication works for publishing.
The API key was used for approved requests, never written into repository files.
