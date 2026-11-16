# Finance harness improvement loop

Active development objective, 2026-11-16: integrate the selected finance evaluation
suite, improve its trustworthiness, and research/test the source-knowledge pipeline.
The user authorized autonomous work and subagent/chat coordination. This is a
persistent goal in the current chat, not a scheduled unattended job or an unbounded
paid inference authorization. Existing spend limits and the original holdout remain.

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

1. Harden exact source-set validation and declared task selection before paid runs.
2. Add tool-free execution for FinEval/FinQA using the existing provider with durable
   spending reservations; distinguish supplied-context performance from full agent.
3. Compare source-scoped retrieval and complete table context on the documented
   cash-flow miss. Preserve native text and old retrieval versions for replay.
4. Add a typed table-evidence fixture and a structurally scored ingestion experiment.
   Compare native parsing, Docling without OCR, and selective OCR on the same sources.
5. Integrate TAT-QA/ConvFinQA using pinned official metrics, shared-document partitions,
   reference-history versus actual-history conditions, and per-conversation denominators.
6. Expand custom cases beyond one company; calibrate semantic judgments with blinded
   finance-literate review before treating strict supported success as established.

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
