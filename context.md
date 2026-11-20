# Working context — 2026-11-16

## Browser workbook milestone — 2026-11-20

Implemented the [browser workbook specification](docs/web-workbook-spec.md):
paged/direct range navigation, keyboard selection, cell inspection with precise
saved values and formula-cache status, stale-citation protection, and guarded
input-only proposals/exports. Export reload checks preserve non-target content,
formulas and comments; audit strings remain text. Complex fidelity-risk workbooks
are read-only and compressed/expanded uploads are bounded.

The browser still works on immutable uploads. Exported copies request Excel
recalculation and report calculation pending; formula editing, structural edits,
server-persistent sessions and Office.js live execution remain later milestones.
The original model/provider and evaluation policies are unchanged. Verification
uses offline/synthetic cases and labeled replay, not a new paid model-quality
assessment or desktop Excel recalculation test.

Verified on the combined working tree: `yarn lint`, all 596 Python tests, the
frontend production build and six Playwright tests pass. The test count includes
pre-existing untracked XBRL tests. The rendered workbook inspector was visually
checked; no paid model batch or desktop Excel recalculation was run for this task.


## Excel planning research — 2026-11-18

Completed an initial primary-source landscape and Office.js constraints review:
[research memo](docs/excel-agent-research-2026-11-18.md). Competitors already offer
cell citations, source links and model updates; differentiation needs a measured,
specific workflow. Proposed first slice: review and update selected model inputs
against source evidence, with approval, stale-target checks and Excel read-back.
No add-in implementation or hands-on competitor comparison was performed.
User/workflow, host and sponsor integration choices await brainstorming. Existing
evaluation reservations and runtime defaults are unchanged.
Documentation verification: `yarn lint` and all 582 tests via `yarn test` pass
in the current working tree, including pre-existing untracked XBRL tests.

## UI branch integration — 2026-11-16

Merged `origin/feat/web-chatbot-mvp` (`02d4038`) into the current
`codex/finance-benchmark-loop` work, preserving its evaluation/harness changes.
The merge required no conflict resolution. Repaired missing optional dependency
entries in `web/package-lock.json`; a clean `npm --prefix web ci` now succeeds.
Verified on the combined working tree: `yarn lint`, all 582 Python tests via
`yarn test`, the TypeScript/production build, and all four Playwright replay tests.
The Python count includes pre-existing untracked XBRL assessment/delivery tests;
those files remain untracked and are not part of this integration. No live model
calls were needed for integration verification. The earlier web-workstream report
below is retained as branch history, not a fresh live acceptance result.

## Web MVP — 2026-11-17

The user decided to show the complete MVP in the browser first (demo 2026-11-17
20:00). Branch `feat/web-chatbot-mvp` starts from `codex/finance-benchmark-loop`
(PR #2); `feat/evaluation-agent-foundation` is an earlier draft of the same work and
was not merged. Scope chosen by the user: cited chat, follow-ups, workbook upload
and range context, approved edits with download; both evidence sets selectable;
OpenRouter `deepseek/deepseek-v4.1-flash-1017`; $1.00 live-spend cap for building
and dogfooding, with a separate allowance for the demo. Design:
[docs/web-mvp-design.md](docs/web-mvp-design.md); plan:
[docs/superpowers/plans/2026-11-17-web-chatbot-mvp.md](docs/superpowers/plans/2026-11-17-web-chatbot-mvp.md).

Verified: 497 Python tests and lint pass (57 new web tests); 4 Playwright replay tests
pass; live browser questions completed with valid citations (single question
$0.0085, follow-up $0.018, workbook proposal $0.0072). The base runtime is unchanged:
chat tools extend `Sources` through `ChatSources`. Desktop Excel opening of exports
is not yet confirmed (AppleScript automation was blocked by an Excel dialog).
Five dogfood rounds scored 82, 97, 97, 98 and 99 out of 100; every defect found was fixed (log: [docs/dogfood/2026-11-17-web-mvp.md](docs/dogfood/2026-11-17-web-mvp.md)). A fresh code review's Important findings are fixed with tests. Shared demo: Cloudflare quick tunnel to `scripts/demo-server.sh` with an access code; the link lasts while this machine runs it.


## Spending preference superseded

The user explicitly removed application spending caps for this Cloudflare work.
`run` and `experiment` now accept `--no-spend-limit`; this supersedes the earlier
aggregate/per-task authorization ceilings for these runs. Costs remain recorded;
time/tool limits and uncertain-billing stops remain. Provider-side limits are
unchanged. Lint and 525 tests pass, including uncapped accounting and interruption
coverage. The [uncapped follow-up](eval/reports/cloudflare-live-2026-11-16-uncapped/report.md)
reran all five spending-stopped questions: four completed (one abstained), three
mechanical passes, one output-length failure. Cost estimate $0.0848396; no spending
stops or uncertain-cost flags. The linked report shows exact inputs and full
outputs for all nine questions, explicitly distinguishing the two batches.

## Cloudflare live follow-up

[Live OpenRouter run](eval/reports/cloudflare-live-2026-11-16-current/report.md):
all nine development questions attempted; four answers, three mechanical passes,
five conservative spending-guard stops. Estimated $0.078254, no uncertain billing
flags in this batch. Local project credential works; environment credential was
rejected. Prior comparison uncertainty remains counted. Combined authorization
accounting is $0.5861111, leaving $0.4138889. Defaults unchanged; semantic caveats
are documented in the report.

## Cloudflare current offline check

[User-requested rerun](eval/reports/cloudflare-current-2026-11-16/report.md) reproduces
8/8 extraction and 6/8 retrieval anchor coverage across nine development questions.
Gross-margin and deck-date evidence remain incomplete in returned windows. No model
calls or answer-accuracy measurement; shared-checkout lint and 523 tests passed.


## Active harness improvement goal

The user now explicitly authorizes model and reasoning-effort selection/comparison.
Historical exact-model settings remain unchanged in saved results. A bounded
[comparison plan](eval/model-effort-comparison-plan.md) is being prepared; existing
aggregate spending limits still apply. The comparison adapter/runner is committed
at `01983f4`, with 500 clean-checkout tests and lint/validation passing. The
[frozen first pilot](eval/assessments/model-effort-v1/pilot-protocol.md) compares
two models at low/high effort on three supplied-evidence development cases;
a fourth selected case is excluded without replacement for reference ambiguity.
The [first live attempt](eval/assessments/model-effort-v1/pilot-report.md) stopped
after one transport failure with unknown billing; zero successful outputs.
The $0.0132189 reservation remains accounted, bringing conservative combined
spend to $0.4946382. No retry, model winner or accuracy gain is established.
The subsequent offline diagnostic repair retains allowlisted transport HTTP
statuses/fixed messages in comparison failures, while stripping arbitrary text.
Independent review and 19 focused tests pass; the original failed pilot is unchanged.
One separately frozen follow-up (`2109681`) returned HTTP 404 and stopped after
its first request. No completed output across either pilot. Both uncertain
reservations remain counted: combined conservative authorization accounting is
$0.5078571, remaining $0.4921429. See the
[follow-up report](eval/assessments/model-effort-v1/followup-report.md).
Further paid comparison calls are stopped for this cycle; H3 integration remains available.
H3's first typed-read component now constructs an authorized FactReader per run,
records actual responses and verifies complete reconstruction and fresh-artifact
replay. It does not yet admit semantic operands or establish model visibility.
See the [component report](eval/assessments/typed-read-authorization-v1/report.md).

H2 progress: numerical kernel `3b4f4ca` and calculation ledger `03e7342` are committed.
The ledger binds trusted admitted evidence, financial compatibility, calculation
ancestry and full replay. Fourteen ledger tests and twelve numeric tests pass,
with two independent ledger reviews. H3's actual source admission, semantic/visibility
boundary and model-tool integration remain pending. See the
[acceptance report](eval/assessments/evidence-calculations-v1/report.md).

The user requested a thorough implementation spec and a continuous benchmark-driven
improvement goal in **Research finance agent harnesses**. The goal is active here;
the earlier **Improve finance evaluation harness** chat remains paused. Its five
untracked XBRL assessment files are preserved and are not owned by this new cycle.
The [specification](harness-improvement-spec.md) defines H0–H6, contracts, migration,
evaluation gates, and budget/holdout boundaries. Two independent Astra reviews
informed it. H1 now implements opt-in model-input receipts and checkpoint v3
policy/source identity binding; legacy behavior remains the default. Independent
review, 470 shared-checkout tests, and 457 clean-commit tests pass. See the
[H1 acceptance report](eval/assessments/model-input-receipts-v1/report.md) for
committed-code verification and limitations. No paid inference accompanied H0/H1.

Latest recorded aggregate spending is $0.4814193 against $1.00 historical
authorization ($0.5185807 nominal remainder). This is not a verified current
account balance. Reconcile all ledgers and account usage before paid execution;
the older authorization paragraph below records a prior balance.

[Recent finance harness research](eval/finance-harness-research-2026-11-16.md)
maps external designs to proposed evidence-linked arithmetic, model-input
receipts, typed-evidence integration, and prospective full-agent evaluation.
The recommendations inform H0–H6; H1 receipt infrastructure is implemented, while
arithmetic and typed-evidence integration remain planned. No benchmark score changed.
Its research-exposure addendum records incidental external examples, including
additional Microsoft exposure, without changing the six frozen reservations.

The [typed-fact delivery diagnostic](eval/assessments/xbrl-evidence-delivery-v1/protocol.md)
now measures existing table reads with exact row locations: 139 reads return all
420 mapped fact occurrences across 412 cells; 84 facts have no mapped cell. This
is an exposed-source, location-assisted coverage check, not retrieval or answer
accuracy. The [opt-in exact-ID reader](eval/reports/xbrl-reader-2026-11-16/report.md) now
reconstructs every occurrence within bounded responses: 484 immediate and 20
deferred. Final case manifests and prospective question assessment remain pending.

The [experimental typed fact export](eval/reports/xbrl-facts-2026-11-16/report.md)
now integrates all 504 exposed ODFL facts with 71 contexts, five units, separate
provenance-bound taxonomy defaults and rebuilt source geometry. Exact numeric and
partial-date representations pass independent source expectations. Seven optional
checks and 431 core tests pass; financial acceptance and rendered visibility remain
unverified. No default policy or reserved evaluation source changes.

## Broader context validation result — 2026-11-16

[Six new development source groups](eval/assessments/financebench-context-v1/progress.md)
are frozen before content inspection: Verizon, Coca-Cola, Costco, Johnson & Johnson,
3M and American Water Works. Independent metadata review confirms existing seed-17
development membership, six distinct companies and no known exposed-company overlap.
All six pinned PDF bodies are acquired and byte-verified with zero failures or
retries. Frozen preparation/native extraction is complete (981 pages, 34,904 lines);
[Outcome-blind annotation](eval/assessments/financebench-context-v1/annotation-report.md)
and independent review are complete for all six cases across ten referenced pages.
Packets preserve ambiguities in 3M, Coca-Cola and Verizon; mapped locations are not
validated financial answers. [Frozen comparison](eval/assessments/financebench-context-v1/comparison-report.md)
now retains complete packets for 0/6, 0/6 and 1/6 at one/three/five reads under
both policies, with 4/6, 5/6 and 5/6 blocked projections. No challenger promotion.
Five other pages lack native text and remain visually unverified. The independently reviewed
[comparison runner](eval/assessments/financebench-context-v1/compare.py) passes
nine synthetic failure/replay tests; six original searches/thirty reads and an exact
replay are complete. [Saved-response diagnosis](eval/assessments/financebench-context-v1/response-size-report.md)
attributes 79.53% of read output characters to extraction metadata. The new opt-in
[returned-page projection](eval/read-extraction-design.md) preserves global warnings
and full-diagnostics provenance while narrowing only response page records.
Independent review and synthetic checks pass. A [controlled assessment wrapper](eval/assessments/financebench-compact-read-v1/progress.md)
verified historical full-mode compatibility and exact replay in both modes. Compact
metadata removed all blocked projections and reduced read output characters
76.05%; complete evidence coverage remained 0/6, 0/6 and 1/6. The explicit mode
is now wired through the CLI, both engines, typed trace grading
and checkpoint identity; full metadata remains the default. A [saved-result and
primary-research review](eval/retrieval-research-2026-11-16.md) identifies unmatched
statement/context locations and potentially useful 3M evidence outside the frozen
packet. Location misses are not exhaustive semantic failures. Two incidentally
exposed paper-example groups are registered for development. A matched page-context
ranking prototype and [assessment runner](eval/assessments/financebench-page-ranking-v1/progress.md)
are independently reviewed. The [frozen comparison](eval/assessments/financebench-page-ranking-v1/report.md)
regressed from 1/6 to 0/6 at five reads under both priorities; pool-25 opportunity
is only 2/6. A [saved-pool oracle diagnosis](eval/assessments/financebench-page-ranking-v1/pool-diagnosis.md)
finds one-window Costco and two-window American Water Works witnesses; four pools
lack required frozen locations. Witnesses remain evaluator-only. Exact replay
passes; no promotion or validation-content access. A [validation reservation](eval/assessments/financebench-page-validation-v1/progress.md)
is complete. Its post-selection audit found two prior-issuer overlaps (Amazon and
Microsoft), retained without replacement; all six selected documents remain closed. The [annotation-validity review](eval/incomplete-judgments-research-2026-11-16.md)
proposes a separate blinded audit without changing historical scores.
A [blinded evidence audit](eval/assessments/financebench-evidence-audit-v1/progress.md)
has locked question-only interpretations from two fresh reviewers and all-six
third-reviewer reconciliation: 16 interpretations, with two cases judged
well-defined, two conditional and two underspecified. Two independent evidence
reviews and a fresh all-case adjudication are locked: 60 requirements and five
complete sets across interpretations. All 223 adjudicated citation occurrences
pass mechanical checks; this is coding-agent judgment, not human financial validation.
Masked packets bind 68 excerpts and 36 uniform review-only pages.
Separately frozen read attribution finds no accepted set covered by either branch.
Only two cases have adjudicated sets; no answer-accuracy claim follows. Independent
reproduction passed. Historical scores remain unchanged.
All 399 tests and lint pass. Four prior TAT-QA issuer identities remain unresolved, so global cross-suite
issuer disjointness is not claimed. No availability-based replacements are allowed.

## Source-context ingestion — 2026-11-16

A [four-source markup inventory](eval/reports/context-markup-2026-11-16/report.md)
reproduces exactly against existing original hashes. None of the extracted cells
has `th`, `headers` or `scope` markup; three filings contain 1,016/452/452 lexical
Inline XBRL numeric tags. These are not validated facts or coverage counts. V3
rejects the Cloudflare release's raw-text context; that disposition is retained.
Explicit-header-only implementation is deferred for this cohort. Investigate a
mature Inline XBRL processor with isolated offline dependencies, diagnostics and
original-markup provenance before adding typed-context tools. No dependency,
extractor default, benchmark score or validation content changed.
An [Arelle preflight](eval/spikes/arelle/README.md) installed version 2.47.2 in a
clean temporary Python 3.13.2 environment and reproduced a missing-schema rejection
under OS network denial. The API returns true and one parsed fact despite two
validation errors: accepted facts remain zero in that negative fixture. A separate
[schema-resolved five-fact fixture](eval/spikes/arelle/typed-values-report.md) now
passes exact value, unit, period and original-cell ancestry checks with six bound
model documents. Eight optional tests pass. Complete runtime hashing, broader
fact types, rendered visibility and issuer extraction remain unverified.
A [versioned guard](eval/spikes/arelle/guarded-values-report.md) now rejects a
confirmed Arelle 2.47.2 negative fractional-timezone mismatch and preserves
duplicate warnings/classifications, quarantining conflicting occurrences. Fifteen
optional tests pass; original five-fact artifacts remain unchanged.
A [controlled 2.47.5 candidate comparison](eval/spikes/arelle/candidate-comparison-report.md)
holds all other distribution versions fixed, verifies import origins and preserves
all scenario semantics. Independent and retained runs match the 15 tests/10 scenarios; no default
promotion or timezone repair is claimed.
A [dimensional context observation](eval/spikes/arelle/dimensions/README.md) now
checks explicit and simple typed dimensions, residual scenario content and namespace
alias equality across 13 occurrences/10 contexts. Six optional tests pass. A separate
[applicability matrix](eval/spikes/arelle/applicability/README.md) checks 14 default/domain/
closed-cube cases: five pass and nine reject despite API success and schema-valid
facts. Seven optional tests pass. Integration with the guarded adapter remains pending.
A [real-filing dependency experiment](eval/reports/xbrl-dependencies-2026-11-16/report.md)
acquired 24 schema/linkbase documents and replayed 2,417 reference edges offline.
The existing ODFL June filing loads all 25 declared documents from a local package,
initially rejected 12 of 504 facts for absent SEC transforms. A subsequent
[pinned transform comparison](eval/spikes/arelle/sec-transforms-report.md) resolves
all twelve against independent source expectations, preserves the other 492 records,
and validates all 504 occurrences. General evidence acceptance remains unverified.
Thirteen core tests cover reference semantics and bounded-acquisition failures.
A [source-occurrence bridge](eval/reports/xbrl-occurrences-2026-11-16/report.md) now
accounts for all 504 facts: 420 exact table-cell joins, 77 outside-table and seven
hidden dispositions. It preserves nested facts and six continuations and matches
every occurrence to the frozen runtime observation. Typed-value integration and
browser visibility remain separate; twelve new core regression tests pass.



## Context-priority challenger — 2026-11-16

[Earlier optional-read preference](eval/reports/context-priority-2026-11-16/report.md)
recovers complete packets for 2/3 cases at five reads, versus 0/3 for the exact
baseline, under the same 32K character limit. NIKE and Ulta improve; Walmart still
fails retrieval. Two wins, zero losses, one tie on exposed development cases; no
default promotion. Fresh validation is required before adoption. All 310 tests
and lint pass, with no paid calls or holdout changes.

## Context-retention result — 2026-11-16

[The original-question context diagnostic](eval/reports/context-retention-2026-11-16/report.md)
retains complete annotated read packets for 1/3, 2/3 and 0/3 tasks at one/three/five
reads, versus delivered coverage of 1/3, 2/3 and 2/3. At five reads the existing
newest-first policy drops early NIKE/Ulta evidence. All snapshots fit the current
32K serialized-output character budget; no policy changed. This is synthetic
context retention, not measured model accuracy. All 304 tests and lint pass.

## Bounded-reading result — 2026-11-16

[The frozen comparison](eval/reports/bounded-reading-2026-11-16/report.md) delivers
complete annotated packets for 1/3 tasks after one read and 2/3 after three/five,
versus 0/3 in search snippets. All three retrieval policies tie. All 45 original
reads succeeded without truncation; 45 separate replay reads verified the traces.
Ulta is complete in one response, NIKE needs a union, and Walmart still misses.
The read result alone establishes neither financial accuracy nor model-visible
context; the separate retention result above finds later evidence loss. This
reading cycle passed 295 tests and lint, with no additional paid spending.

## Evidence-component diagnostics — 2026-11-16

[Replay-bound component coverage](eval/reports/evidence-components-2026-11-16/report.md)
shows the same result for all three saved retrieval conditions: complete annotated
packets in parent passages for 2/3 tasks at top three/five, but 0/3 in returned
snippets. NIKE requires a union of parent passages; Ulta has a complete first
parent. This posthoc development diagnostic separates read opportunities from
text actually returned, without changing page scores or claiming answer accuracy.
All 278 tests and lint pass. Bounded reading is the next evaluation question.

## Broader assessment preparation — 2026-11-16

The [locked native-HTML assessment plan](eval/assessments/native-html-v1/plan.md)
records a metadata-verified six-filing proposal across three new issuers, with 21
positive question slots and three publication-availability controls. The first frozen acquisition attempt returned HTTP 403 for all six sources
(0/6 verified downloads). A separately frozen issuer-delivery attempt verified
2/6 copies (both Old Dominion); Casey’s returned HTTP 403 and Ameren delivered
rendered viewer HTML that remains ineligible. Offline extraction succeeded on the
two copies without a completeness claim. A separately frozen complete-submission
attempt returned four HTTP 403 responses (zero containers); those routes will not
be automatically retried. All six dispositions remain recorded in
[assessment progress](eval/assessments/native-html-v1/progress.md). Questions are not authored. A separate search-only runner
passes synthetic integrity/interruption checks. Separate receipt-bound grading
now validates replay and complete evidence alternatives. Selected-source cutoff
controls now distinguish unavailable, unknown and observed-available artifacts;
full provenance gates and real cohort acquisition remain pending.
Synthetic review found hidden-text and block-boundary defects in legacy HTML text
extraction. An opt-in `native-html-text-v2` repair passes adversarial tests, with
explicit CSS/completeness limitations; legacy replay and frozen corpora remain
unchanged. This is preparation, not a new accuracy result.


## Template extraction repair — 2026-11-16

[Opt-in sidecar v3](eval/reports/table-template-2026-11-16/report.md) isolates inert
HTML templates from visible table geometry and text. Seven new synthetic tests
pass; four v2 sidecars replay exactly. Explicit v3 selection now reaches tools, run-protocol v4 and separate grading;
default tools and historical protocols retain v2. All 36 historical tool responses
replay exactly. A real assessment still requires a new freeze.
This is a standalone extraction repair, not improved financial accuracy.

## Raw table runtime — 2026-11-16

[Fixed offline probe](eval/reports/table-runtime-2026-11-16/report.md): standalone
raw-table reads cover all required cells for 4/4 explicit-window controls, while
original-question search plus one read improves 1/4 → 2/4 after excluding redundant
prefix rows. Correct tables rank first 3/4 and within three 4/4. The raw grader does not infer semantic or typed answer success.
Default graph/citations remain unchanged; no additional paid inference occurred.
A frozen soft-prefix weighting challenger remained 2/4, with no paired wins or
losses. Both earlier versions replay exactly; v2 remains the default. The negative
result is retained, and broader uninspected development assessment is next.


## Statement-context retrieval — 2026-11-16

[Equal-budget context terms](eval/reports/statement-context-2026-11-16/report.md)
left coverage at 2/4 pages and 2/3 complete tasks, while Walmart’s expected
candidate-page coverage fell from 1/2 to 0/2. No promotion. The prior component
policy replays exactly. Passage diagnostics do not support blaming numeric length
or missing main-passage headers for these misses.

## DPO retrieval experiment — 2026-11-16

[Question-only component retrieval](eval/reports/dpo-retrieval-2026-11-16/report.md)
used seven searches versus three but remained at 2/4 annotated pages and 2/3 tasks
with complete page coverage. No paired wins/losses; default unchanged. One missing
Walmart page entered the candidate pool but was discarded, and the other never
entered it. The negative result and exact baseline replay are retained.

## PDF visual quality review — 2026-11-16

[Five rendered pages](eval/reports/pdf-visual-quality-2026-11-16/report.md) distinguish
Walmart retrieval misses from missing text and flag Ulta’s fiscal-year convention.
A ninth content-bound reference issue preserves original gold. Page diagnostics
now expose native-text counts and line ranges; all 419 extracted pages replay
with identical text and locations. No OCR, inference or score changes occurred.

## Source-quality iteration — 2026-11-16

Whole-document diagnostics bind originals, extracted text, and the full manifest.
Three-task retrieval reaches 2/4 annotated pages at five hits; declared-document
scoping improves first-hit recall from 1/4 to 2/4 without fixing the remaining task.
Native HTML v2 fixes explicit-hidden contamination and retains raw headers/captions;
four evaluator-only packets check source/period/sign/scale associations. Lint and
271 tests pass. Full-agent FinanceBench inference and human adjudication remain
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

## Historical authorization after the frozen November 7 batch

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
