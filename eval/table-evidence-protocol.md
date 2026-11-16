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
The v2 sidecar suppresses explicit hidden content, preserves raw header attributes
and captions, and separates block text. All frozen release cell IDs/text replayed
unchanged; fixture sidecar identities were deliberately promoted to v2. Original
v1 artifacts remain unchanged. External CSS and inferred header links remain unresolved. This protocol does not alter the original task corpus or holdout.

`provenance.table_evaluation.grade_table_packet` now checks strict packet fields,
source/table/version/hash identity, every included cell against the sidecar,
required component associations, typed numeric values/units, and the size limit.
Synthetic complete packets pass all four fixtures. Negative tests reject missing
components, wrong-table duplicate values, wrong periods, split-sign omissions,
per-share scaling, fabricated locations, duplicates, and unsupported extra claims.
This is a grader check, not evidence that a runtime retrieved the packet.

Additional independent adversarial review found and fixed spaced CSS importance,
hidden self-closing rows/wrappers, additional block-number boundaries, and Boolean
geometry comparing equal to integers. Hidden empty cells in the real filing retain
geometry and suppression until their explicit/implicit end. Canonical JSON cell
comparison distinguishes Boolean and numeric coordinates/spans. All seven frozen
benchmark score artifacts still reproduce exactly after these changes.

Cross-chat review confirmed the four cell associations and identified a missing
typed-period check. Packets now state instant/duration, period end, and duration
months where applicable; correct cells with a wrong typed period fail. The per-share
fixture also requires its adjacent dollar-symbol cell. USD remains the development
task currency convention: a dollar symbol alone does not independently establish
which dollar currency applies. Do not claim explicit ISO-currency provenance.
