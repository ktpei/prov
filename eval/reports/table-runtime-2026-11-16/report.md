# Raw table-tool development probe — 2026-11-16

The fixed protocol ran offline under clean commit `e7c3e94`. No model or network
calls occurred. Actual public tool calls/responses are retained locally at
`runs/table-runtime-2026-11-16/report.json`; the [summary](baseline-summary.json)
records hashes, input selections, sizes, failures, and grading.

| Condition | All required cells in one read | Expected table at rank 1 | Expected table by rank 3 |
|---|---:|---:|---:|
| Explicit-window control | 4/4 | Not measured | Not measured |
| Original question → top table → first 3 matched rows | 1/4 | 3/4 | 4/4 |

The explicit-window control uses evaluator-selected tables/rows. It establishes
bounded read capacity, not retrieval quality. Its four responses use 3,087–9,668
compact JSON characters, below the 12,000-character cap. The question-search
condition uses no oracle table/row choice, no query rewriting, and one read per
question. All attempts are retained; no repair or smaller-window retry occurred.

- **fresh-03:** search selected the free-cash-flow reconciliation (`table-12`)
  instead of the requested cash-flow statement (`table-8`, ranked second).
  The duplicate amount in the wrong table correctly failed source/table context.
- **fresh-01:** the correct reconciliation table ranked first, but the three row
  candidates included two prefix/header rows and only the non-GAAP R&D row.
  The GAAP R&D value/label were missing from the read.
- **fresh-02:** the correct balance sheet ranked first, but selected rows omitted
  total current assets. Current-liability context alone did not pass.
- **per-share-scale:** the actual read contained all required cells, including
  period, unit exception, loss sign and dollar symbol.

The raw-context grader validates source/sidecar/manifest identities, exact cells
and captions, size, and required-cell presence. Association correctness, typed
answer correctness, and agent selection remain explicitly **not measured**.
These are four inspected development fixtures, not general finance accuracy or a
heldout result. Default graph tools and line-citation behavior are unchanged.

Next controlled change: exclude prefix/header rows already guaranteed by the read
policy from ranked value-row candidates, without altering table ranking. Preserve
this baseline and measure the revised selection separately. Wrong-table and
missing-asset failures remain visible until a separately reviewed change fixes them.
