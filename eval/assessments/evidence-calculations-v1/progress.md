# H2 progress: numerical kernel

Historical kernel milestone · 2026-11-16 · implementation `3b4f4ca`

Superseded by the [H2 ledger acceptance report](report.md). The incomplete status
and next-work descriptions below describe the earlier kernel-only milestone.

[Frozen protocol](protocol.md), commits `015e7e9` and pre-implementation clarification
`13234fe`. Baseline `82aa34b`. Synthetic-only infrastructure work; no paid inference,
financial source selection, heldout inspection, or accuracy experiment.

## Implemented

Internal `provenance.calculation_numeric.evaluate_numeric` supports six bounded
operations using standard-library Decimal. It checks lexical/operand/exponent
bounds before arithmetic, scales exactly, preserves ordered precision-34 results,
separates arithmetic/display flags, and applies explicit half-even display rounding.
Errors have stable codes. The response is bounded to 12,000 serialized characters.
This pure kernel takes numerical values internally; it is not a model tool,
admission authority, financial compatibility checker, or calculation ledger.

Independent numerical review supplied exact cancellation, order, precision and
large-value fixtures. Implementation review reproduced ambient DefaultContext
flag contamination and exponent capitalization drift. Explicit contexts and
canonical Decimal strings now prevent both; whole-record regression tests pass.

## Verification

- Twelve focused test groups pass: ordered cancellation, formulas/flags, scales,
  mixed fraction/percent rates, internal bounds, half-even ties, large displays,
  lexical bounds, invalid inputs, result bounds, zero/baseline failures, contract
  errors, response-size boundaries, and ambient-context independence.
- Independent read-only Astra review confirms no remaining numerical blocker.
- Shared checkout: `yarn lint` and **482 tests passed**, including 13 pre-existing
  untracked tests belonging to the paused XBRL assessment. Those files are untouched.
- Clean detached checkout at `3b4f4ca`: Ruff check/format, corpus validation and
  **469 tests passed** using the existing locked dependency environment. Git status
  was clean afterward. Existing SQLite ResourceWarnings remain unrelated to this
  component. No live provider was invoked.

## Required next work

The independent financial-contract review recommends a trusted immutable
accepted-operand snapshot; no caller-controlled `accepted: true` field can confer
authority. Preserve every normalized attribute's origin and support, and never
upgrade XBRL structural delivery to financial correctness or apply scale twice.

The ledger must validate entity/unit/currency/basis/actual-guidance/scope/metric
compatibility, reject unknown required attributes, bind references to same-run
content, preserve comparison periods, consume precision results rather than display
values, enforce depth 16, and replay arithmetic plus metadata/lineage. Structural
derived metrics exclude occurrence IDs/dates while retaining operation/ordered
metric identities. Output unit is an assertion, never an implicit conversion.

Before ledger implementation freeze cadence semantics: equal duration lengths or
independently validated equal whole-calendar-month spans; no automatic 52/53-week
equivalence. Reject comparison-valued inputs in initial arithmetic rather than
laundering a two-period result into a single current period. Financial-role admission
for margin and full source/read authorization remain explicit trusted boundaries.

The future full record must be serialized and bounded before registry mutation;
kernel response size alone cannot guarantee this. H3 supplies real reader admission,
final-request evidence visibility and controller tool-budget integration. H2 cannot
be accepted merely because this numerical component passes. No end-to-end financial
improvement or default runtime change is claimed.
