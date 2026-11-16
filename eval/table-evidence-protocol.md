# Connected table-evidence acceptance

The [four frozen development fixtures](table-evidence-fixtures.json) bind exact
cells to source hashes and a sidecar version. Two coding agents inspected the
original HTML and structure; these are not human-adjudicated financial labels.
They remain evaluator-only and must not enter extraction, search queries, or model
instructions. No table-aware runtime read is claimed yet.

A candidate must return one connected packet, at most 12,000 serialized characters,
containing the required metric labels, period hierarchy, scale, values, and split
sign cells. A source/table/version/hash mismatch fails. Matching values somewhere
in disconnected windows cannot pass. Typed values are assessed separately from
cell presence: cash-outflow magnitude is positive while statement value is negative;
per-share numbers must not inherit the table's thousands scale.

Required negatives:

- Same purchases amount in the free-cash-flow reconciliation instead of the
  requested cash-flow statement.
- Same year under nine-month instead of three-month headers.
- Prior-year column, adjacent software row, or wrong source document.
- Missing closing-parenthesis sign cell or missing units/period.
- Per-share loss multiplied by one thousand.
- Correct text with fabricated cell IDs, geometry, or original locations.
- Oversized or disconnected packets, and hidden text masquerading as visible values.

Report component presence, association correctness, numeric/unit correctness, and
complete-packet success separately. Keep unresolved header relationships visible.
The current v1 sidecar has a known explicit-hidden-text defect; v2 remediation is
in progress. Version promotion requires replay of all fixture cells and negative
checks. This protocol does not alter the original task corpus or holdout.
