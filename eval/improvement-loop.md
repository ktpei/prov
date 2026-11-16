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
