# Finance harness improvement loop

Active objective, 2026-11-16, in **Research finance agent harnesses**: continuously
improve the research harness through reproducible benchmark-driven cycles under
the [implementation specification](../harness-improvement-spec.md). The earlier
**Improve finance evaluation harness** chat remains paused; its draft XBRL assessment
work is preserved. The user authorized this new goal and subagent/context use.
This is not a scheduled unattended job or unbounded paid inference authorization.
Existing spending limits, source reservations and original holdout rules remain.

## H0 — specification and continuity

- Wrote versioned receipt, evidence, calculation, answer and checkpoint contracts.
- Inspected relevant evaluation, OCR and UI handoff chats; retained ownership and
  compatibility boundaries rather than resuming another chat's paused drafts.
- Independent Astra architecture and evaluation reviews supplied acceptance and
  promotion requirements. Financial semantics remain distinct from delivery.
- No runtime defaults, frozen scores, reserved selections or paid inference changed.
- Review corrections define H1 legacy evidence references, explicit checkpoint
  migration, calculator formulas/bounds, final-attempt visibility, all-required
  strict success and a failure-inclusive adjudicable denominator.
- Verification: `yarn lint` and 453 tests passed in the current shared checkout,
  including the pre-existing untracked assessment tests; SQLite ResourceWarnings
  remain. Local spec links, code fences and whitespace checks passed. This is
  documentation verification, not clean-commit experiment acceptance.
- Next cycle: H1 model-input receipts and checkpoint policy identities. Freeze
  its bounded implementation/verification plan before changes; use synthetic and
  saved legacy artifacts without opening heldout content.

## H1 — model-input receipts

Implemented the opt-in `trace-receipts-v1` OpenRouter/LangGraph profile under the
[frozen protocol](assessments/model-input-receipts-v1/protocol.md). Receipts capture
canonical, projected, and mapped inputs before dispatch, with replayed inventories
and policy identities. Checkpoint v3 binds full source metadata and effective policy;
legacy checkpoints cannot silently migrate. Legacy behavior remains the default.

Independent Astra review reproduced four verifier/configuration gaps; all were
fixed and added to regression tests. Lint and 470 tests pass in the shared checkout,
including 13 tests belonging to the paused assessment chat. See the
[acceptance report](assessments/model-input-receipts-v1/report.md): clean commit
`3dcd09b` passes lint, validation and 457 tests. No paid inference, heldout
inspection, or financial accuracy gain.

The [methodology research loop](harness-methodology-research-loop.md) feeds this
implementation loop. Retain existing no-blind-retry protection; queue its synthetic
external-success/local-acknowledgement crash test as a separate recovery check.
Defer Inspect/Temporal migration. Next implementation increment is H2's bounded,
evidence-linked arithmetic with synthetic financial-scope and replay tests.
The [reference-contract research](harness-reference-contract-research-2026-11-16.md)
reinforces Decimal and financial-operand validation. H3 must preserve budget and
deadline exceptions as controller stops rather than repairable tool errors.

## H2 — numerical component, ledger pending

Frozen [protocol](assessments/evidence-calculations-v1/protocol.md) before code;
independent numerical/financial-contract reviewers clarified internal bounds,
exact scaling, structural derived metrics and comparison-period identity. The
kernel is committed at `3b4f4ca`; 12 focused tests and 482 shared-checkout tests
pass with lint; clean commit `3b4f4ca` passes 469 tests and the same lint/validation
checks. Review found ambient Decimal flags/exponent formatting could
alter records; both are fixed with full-record regression coverage.

This is a required component, not H2 completion. No model-facing calculator,
financial acceptance or accuracy gain is claimed. Next: immutable admitted-evidence
snapshot, compatibility checks, calculation references/ancestry and independent
replay. See the [progress report](assessments/evidence-calculations-v1/progress.md).
No paid calls or heldout content inspection occurred.

## H2 — trusted-snapshot ledger

Frozen ledger contract `364fe8a`; implementation `03e7342`. Added immutable
same-run evidence/calculation references, financial compatibility checks, structural
metric and comparison-period identities, precision-preserving chains, depth/size
limits, atomic failure and full replay. Fourteen ledger tests and two independent
read-only reviews pass; shared-checkout lint and 496 tests pass. Clean commit
`03e7342` passes the same checks with 483 tests. See the
[acceptance report](assessments/evidence-calculations-v1/report.md) for clean checks
and the synthetic trusted-admission boundary. H3 still owns real reader admission,
claim visibility and model-tool budget integration. No paid calls or accuracy gain.

## M1 — model/effort comparison and transport diagnostics

Comparison infrastructure `01983f4` passed 500 clean-checkout tests and lint.
Protocol `1422bad` froze four selected exposed development cases, with 3M excluded
without replacement after independent pre-output reference review. Three eligible
cases were assigned to DeepSeek Flash and GPT-6 Luna at explicit low/high effort.
The supplied-evidence condition measures interpretation, not retrieval.

The first live request failed before any usage/output returned; all subsequent
rows stopped. See the [negative result](assessments/model-effort-v1/pilot-report.md)
and committed accounting `cb8a0ae`. Preserve $0.0132189 uncertain reservation;
combined conservative authorization accounting is $0.4946382. Unchanged aggregate
key usage is not proof of zero request cost. No model winner or quality gain.

The next offline repair preserves only the existing transport's exact fixed
messages and ASCII HTTP status vocabulary through comparison sanitization.
Arbitrary messages, near matches, headers and URLs remain discarded. Shared
transport behavior, no-retry policy and uncertain accounting are unchanged.
Independent Astra review passed all 19 adapter/runner tests, including real
transport-to-ledger HTTP 400/401/429/500 failures and secret-bearing negative
fixtures. Full shared-checkout `yarn lint` and 515 tests pass (including the 13
untracked tests owned by the paused assessment chat). This diagnostic repair
cannot recover the original failure cause.
No additional paid call was made. A revised live protocol and explicit treatment
of the retained uncertain reservation are required before another trial.

## M2 — one deliberate diagnostic follow-up

Independent review and protocol `2109681` authorized one explicitly recorded
repeat within the existing budget, carrying the prior uncertain charge in full.
The clean checkout passed 19 focused tests. First request returned HTTP 404;
diagnostics survived, all later rows stopped, and no successful outputs exist.
Read-only provider metadata still lists the model/provider; specific rejection
cause remains unknown. See the [report](assessments/model-effort-v1/followup-report.md).
Two attempts across both pilots retain $0.0264378 uncertain reservations; combined
conservative accounting is $0.5078571, remaining $0.4921429. No additional paid
follow-up this cycle. Continue offline diagnosis and H3 source/visibility integration;
do not mistake an infrastructure fix or failed transport for measured finance quality.

## Repeatable cycle

1. Select one failure class from source QA, scorer adversarial tests, or a declared
   development experiment. Record the hypothesis and acceptance check before changing it.
2. Research primary sources and inspect actual schemas/scorers. Pin file bytes and
   revisions. Preserve conflicting references instead of quietly repairing gold.
3. Implement a focused change, with independent workers assigned exclusive files
   or worktrees where useful. Lead reviews actual diffs and integrates changes.
4. Run relevant adversarial checks plus `corepack yarn lint` and `corepack yarn test`.
   Repeat saved legacy evaluation offline when source or replay behavior changes.
5. Compare the same selected tasks and budgets. Retain missing/failed attempts,
   raw outputs, references, scorer versions and uncertainty. Keep preparation,
   retrieval anchors, mechanical accuracy, and reviewed support distinct.
6. Update this ledger and relevant context, commit an atomic improvement, then
   choose the next failure class. Never tune on the original 15-task holdout.

## Cycle 1 — external benchmark foundation

- Baseline verified: lint and 79 tests passed; pre-existing SQLite ResourceWarnings.
- Preserved the previously approved benchmark plan in commit `940609f`.
- Coordinated with **Research finance evals comparison** and **Evaluate OCR for
  source ingestion**; the latter reproduced the cash-flow retrieval/context miss.
- Independent Astra research and scoring audits; isolated Sol implementation worker
  for core adapters, with lead review and additional actual-release validation.
- Pinned and hash-verified four input files; imported three dataset families.
- Added input/reference separation, internal development selection, strict adapted
  scorers, manifest-bound submissions, and complete selected-task denominators.
- Upstream QA: 12 FinQA empty display answers remain usable via execution targets;
  three contradictory CFA-Easy labels remain unresolved and unscored automatically.
- Combined verification: lint and **102 tests passed** (79 existing plus 23 new).
- No new paid inference, human finance review, or heldout model run.

## Next work queue

The user authorized choosing/comparing models and reasoning efforts. Prepare the
[bounded comparison](model-effort-comparison-plan.md) alongside H2/H3, preserving
historical results and reconciling spending before any trial. No comparison has
run yet; capability, accounting and aggregate-budget gates precede inference.

1. H1 accepted infrastructure: retain regression coverage; add the separately
   proposed external-success/local-acknowledgement crash test before recovery changes.
2. H2 accepted as trusted-snapshot infrastructure; retain numerical/compatibility
   replay tests while H3 supplies actual source admission and model-tool exposure.
3. H3: integrate versioned answers and typed discovery/read/claim contracts.
4. H4: compare requirement-aware context retention and narrow workflow instructions.
5. H5: run source-accepted, preregistered full-agent development comparisons within
   reconciled authorization; calibrate semantic review and retain all failures.
6. H6: select the next measured bottleneck, with fresh confirmation before promotion.

The prior queue's benchmark adapters and tool-free pilots are implemented. Later
reports in `context.md` also record negative ranking/retention comparisons, compact
PDF metadata savings without coverage improvement, and exact-ID XBRL delivery.
None establishes a broad end-to-end accuracy gain. Keep the dated cycles below
as history rather than rewriting their then-current results.

Perfection is not a measurable stopping criterion. A promotion needs evidence on
predeclared cases, a clear failure taxonomy, and no regression in critical support,
unit/period, leakage, or abstention checks. Unrun comparisons remain proposed.

## Cycle 2 — bounded execution

- Tool-free OpenRouter execution now uses the existing adapter with benchmark-specific
  instructions and no bound tools. Original research defaults remain unchanged.
- Every selected ID is persisted before execution; pending reservations survive
  crashes, uncertain charges stop the batch, and no automatic retry/repair occurs.
- Independent review prompted generation-setting provenance, invalid empty-output
  handling, and retained sanitized truncated-response diagnostics with known charges.
- Lint and **109 tests passed** before the first external live pilot.
- Account preflight found the inherited environment key invalid (HTTP 401); the
  existing local `.env` key succeeded with a $1 daily limit and $1 remaining.
  Credentials were not printed, copied into artifacts, or changed.
- Exact requested model remains available. Catalog maximum scheduled rates are
  $0.30/$1.20 per million input/output tokens; pilot accounting will conservatively
  retain the established $0.60/$2.40 rates. No inference occurred during preflight.

- Packet experiment preflight now requires unique task IDs, explicit development
  labels, and exact source ID/hash equality before provider construction. Its ledger
  includes the full selection, benchmark hash, and skipped/pending/completed status.
  Historical task files are unchanged; a new explicitly labeled development manifest
  is required when an older file lacks split labels.

## Cycle 2 measured pilot

Ten tasks ran once under a committed protocol and clean frozen runtime. Five
FinEval choice passes, FinQA 2/3 adapted scalar passes, and two FinanceBench oracle
responses with automatic accuracy unset. Cost $0.0161622; remaining authorization
$0.5476339. See the [report](reports/external-pilot-2026-11-16/report.md).
Independent review found upstream question and convention ambiguity; original
scores remain unchanged. Next: content-bound reference issue registry and broader
source/document partitions before more inference.

## Cycle 3 — reference quality and overlap

- Added six content-bound unresolved reference issues: three CFA label conflicts,
  one underspecified FinQA question, and two FinanceBench interpretation/wording
  ambiguities. New preparation annotates references only; inputs/gold are unchanged.
- New runs skip unresolved references before making paid requests, retain them in
  the selection, and leave accuracy unset. Frozen pilot artifacts remain unchanged.
- Partition v2 groups FinQA pages by `TICKER/YEAR`; legacy v1 is still replayable.
  Reviewed report groups are forced into development. This prevents the previously
  seen MRO report from accidentally moving into a newly computed final partition.
- Full expansion research found all 421 ConvFinQA dev conversations overlap FinQA
  dev by source page. Shared report partitions are required; independent coverage
  cannot be claimed. TAT-QA's stable table IDs support context, not report, grouping.
- Lint and **121 tests passed** after reference/exposure integration. A new 100-task
  FinQA manifest was prepared offline with the reference registry and report groups.
- TAT-QA/ConvFinQA files acquired with pinned archive/member hashes; adapter and
  official-metric integration is in progress. No additional inference spending.

## Cycle 4 — table and conversation integration

- Added pure TAT-QA/ConvFinQA adapters and history projections. Imported all 1,668
  table questions and 421 conversations/1,490 turns from pinned development files.
- Vendored the official TAT-QA scorer with MIT license and byte-hash tests; only
  its package-relative import changes. Optional locked metric dependencies are
  installed by `yarn test`. Wrapper-v2 protects zero/scientific numeric values and
  rejects blank outputs; official EM/F1 and scale accuracy remain separate.
- Added complete turn/conversation denominators and preserved outer completion
  status. Conversation execution is not yet wired; scalar program accuracy is
  deliberately not called official execution/program accuracy.
- Independent review found and fixed a missing CLI exposure-override argument and
  upstream scientific-notation false passes. An actual preparation CLI regression
  now proves exposed reports stay in development. Superseding local manifests:
  `finqa-reviewed-v3`, `tatqa-reviewed-v2`, `convfinqa-reviewed-v2`.
- Lint and **141 tests passed**; all four original pilot scores reproduced exactly.
  The official scorer matched all TAT-QA references against themselves (compatibility
  check only). No additional paid model calls or original holdout evaluation.

## Cycle 5 — bounded conversations and source structure

- Integrated single-attempt conversation execution with global/conversation/turn
  budgets, durable reservations, complete denominators and actual/reference-history
  separation. Independent review caught oversized numeric strings entering history;
  scorer-aligned validation now stops them before later requests.
- Added separately versioned native HTML cell geometry. The pinned Cloudflare release
  yields 16 tables, 253 rows, 2,682 cells; split parentheses and empty cells survive.
  These are extraction counts, not financial semantic accuracy.
- Added metadata-hash-bound FinanceBench whole-PDF assembly, excluding evaluator gold.
  Three originals downloaded/extracted: NIKE_2023_10K, ULTABEAUTY_2023Q4_EARNINGS,
  WALMART_2018_10K. Missing fontTools warnings require extraction QA before use.
  Selected metadata conflicts reject assembly; the upstream Foot Locker year conflict
  is recorded without guessing a resolution. Full-agent execution remains disabled.
- Lint and 161 tests passed. No additional paid calls; remaining authorization is
  $0.5476339. Native table review is coordinated with the ingestion research chat.

## Cycle 6 — measured table/conversation pilot

The frozen 22-request pilot completed under clean commit `17ee7a4`; all scores
reproduced from saved submissions. TAT-QA official EM/F1/scale matched 4/4;
ConvFinQA both conditions scored 6/9 turns and 0/2 whole conversations.
Cost $0.0290532; remaining authorization $0.5185807. Source-level annotation and
scale review remains separate from these fixed scores. See the
[report](reports/expansion-pilot-2026-11-16/report.md).

## Cycle 7 — source-quality separation

- PDF diagnostics now preserve warning counts/samples per page and package versions.
  Five Nike font-risk pages produced identical text with/without fontTools 4.68.0;
  warnings fell 87 → 0. No extraction improvement or dependency promotion is claimed.
- FinanceBench corpus binding v2 hashes the complete source manifest, preventing
  silent page-map changes. Three-document v2 originals/text match the prior corpus.
- Question-only top-five retrieval reached 2/4 annotated pages and covered 2/3 tasks;
  the Walmart task missed both required pages. Exact excerpt concordance 2/4 reflects
  retained dash characters in the two nonmatches, not proven missing information.
- Four evaluator-only table fixtures bind source/table/period/scale/sign roles.
  Sidecar v2 repairs hidden text and retains explicit caption/header metadata.
  No additional paid inference or original holdout access.

## Cycle 8 — scoped retrieval and adversarial table packets

Declared-document scoping improves top-one annotated-page recall 1/4 → 2/4 on
the same three inspected tasks; top-five remains 2/4 and Walmart remains unresolved.
Queries contain no gold. This is exploratory development evidence, not heldout QA.
Sidecar v2 preserves all release cell IDs/text while fixing explicit-hidden and
block-boundary contamination. Four structural packets and adversarial negatives
are graded separately from any agent run. Lint and 189 tests passed; no paid calls.

## Cycle 9 — actual raw-table tool path

Standalone TableSources validates immutable originals, hashes sidecars/manifests,
returns copied raw cells, and rejects oversized responses atomically. No default
graph/citation changes. The distinct raw-read grader rejects forged captions,
manifest identities, and error-bearing responses; semantic/typed correctness stays
unmeasured. Lint and 204 tests passed.

Fixed clean-code probe: explicit-window controls 4/4 complete component coverage;
question-search plus one read 1/4, despite correct table 3/4 at rank 1 and 4/4 by rank 3.
Wrong-table duplicate values and missing GAAP/asset rows remain actual failures.
See [report](reports/table-runtime-2026-11-16/report.md). No paid calls occurred.

## Cycle 10 — nonredundant table row candidates

A separately committed challenger excludes prefix rows already returned by every
read from value-row candidates. Table scores/order and all other fixed conditions
are unchanged. Complete raw-context coverage improves 1/4 → 2/4; window controls
remain 4/4. R&D is fixed, while wrong-table cash flow and missing current assets
remain failures. Every baseline tool-response hash replays exactly under v1.
Lint and 206 tests passed. Remaining model-spend authorization is $0.5185807;
this and all ingestion cycles made zero paid calls. Next: table-type and multi-metric
selection, broader development fixtures, and explicit graph/citation profiling.
