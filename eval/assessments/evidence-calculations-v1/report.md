# H2 evidence-linked calculation acceptance

2026-11-16 · synthetic-only infrastructure acceptance

Numerical component `3b4f4ca`; ledger implementation `03e7342`.
Frozen [protocol](protocol.md) and [ledger contract](ledger-contract.md), committed
before their implementations. [Earlier kernel milestone](progress.md).

## Delivered

The internal CalculationLedger snapshots a trusted admission inventory and resolves
only same-run evidence or earlier calculation references. It checks declared
financial compatibility, executes the bounded Decimal kernel, and records complete
request/operand identities, scope/period/unit metadata, derived metric identity,
depth and all upstream evidence IDs. Replay rebuilds the entire record, including
metadata and provenance bindings, from an independently trusted snapshot.

Current/prior margin calculations can feed a percentage-point comparison without
losing either period. Chains use the precision-limited value rather than its display
rounding. Scale/rate conversion is explicit; unknown attributes, wrong currencies,
periods, scope, accounting basis, actual/guidance status and margin roles reject.
Copied inputs/outputs cannot mutate accepted state. Full response-size and depth
checks happen before mutation. Ordered operands remain authoritative; algebraic
reassociation is not a valid replay shortcut under finite precision.

## Evidence and verification

- Fourteen ledger test groups plus twelve numerical test groups cover current/prior
  margin chaining, financial incompatibilities, unknown attributes, rate conversion,
  precision preservation, period comparability, admission/support validation,
  reference/depth/size failures, mutation, replay tampering and ordered arithmetic.
- Two independent read-only Astra ledger reviews found no material blocker.
  Additional probes covered request mutation, added-rate chaining, reversed replay,
  self-cycles, forged lineage/precision identities, and failures preserving state.
- Shared checkout: `yarn lint` and **496 tests passed**. This includes 13 pre-existing
  untracked tests owned by the paused XBRL assessment; none was edited or committed.
- Clean detached checkout at `03e7342`: Ruff check/format, corpus validation and
  **483 tests passed**, using the existing locked dependency environment. Git
  status was clean afterward. This excludes the paused chat's 13 untracked tests.

## Acceptance boundary

This accepts H2's arithmetic/compatibility/replay infrastructure relative to a
trusted admission snapshot, after clean verification. It does not independently
establish that a source parser or model proposed the right financial interpretation.
Model-proposed attribution remains visible. Caller-supplied accepted flags confer
no authority; the constructor is an internal controller boundary, not a tool.

No live source admission or model-facing calculator is enabled. H3 must establish
actual read authorization and complete support reconstruction, semantic admission,
final-request visibility, versioned answers and controller tool budgets before
exposing this capability. A matching metadata tuple does not prove facts are additive
or free of double counting. Derived metrics use structural identity; ratio/margin
remain distinct. Comparison-valued results cannot be further arithmetic operands
in v1. These conservative limits are explicit in the frozen contract.

No paid model calls, reserved content inspection, new source selection, or financial
accuracy comparison occurred. Existing SQLite ResourceWarnings remain. Legacy
agent tools/defaults, frozen benchmark scores and reservation dispositions are
unchanged. The ongoing improvement goal remains active.

## Next work

Implement H3's actual reader/answer/visibility boundary. In parallel, prepare the
user-authorized [model/effort comparison](../../model-effort-comparison-plan.md),
with explicit configuration, usage accounting, aggregate reservations and blinded
grading. Reconcile spending and freeze feasible tasks/caps before any paid trial.
