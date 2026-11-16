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

## Controlled row-candidate iteration

The [challenger protocol](prefix-candidates-protocol.json) was committed before
execution under clean `288b722`. Search v2 excludes the first five physical rows
from read candidates because the unchanged read policy already includes them.
Table scores/order, original queries, the first-three rule, read windows, response
cap, and fixtures are unchanged. V1 remains selectable for exact baseline replay.

Required raw context improves **1/4 → 2/4**: GAAP and non-GAAP R&D now arrive
together. Explicit-window controls remain4/4. The cash-flow statement still loses
to its reconciliation distractor, and the balance-sheet read still omits current
assets. No semantic or financial accuracy is inferred. Table scores and order
matched exactly for all four cases; every baseline tool-response hash reproduced.
[Challenger hashes and outcomes](prefix-candidates-summary.json).

This is a measured development improvement on inspected fixtures, not an unseen
quality estimate. Further work should separately address table-type disambiguation
and multi-metric row selection, then assess broader, uninspected development cases.
Do not hide these remaining failures by inserting fixture-selected rows.

## Preregistered soft-prefix candidate experiment

Search v3 is opt-in; v2 remains the default. The
[protocol](soft-prefix-protocol.json) changes only body-row ordering: retain the
existing corpus-wide BM25 statistics, multiply query-term IDF by 0.25 for terms
present in the table caption/first five rows, and by 1 otherwise. Rerank all
matching body rows before the eight-candidate limit. Table scores/order, literal
tokenization, first-three selection, read windows and budgets remain unchanged.
The constant is a declared heuristic, not a fitted or literature-derived optimum.

This tests whether repeated positional context crowds out body-specific evidence.
It can also penalize useful dates, units, or metrics; these are retained with
positive weight. It cannot fix a wrong top-ranked table. Synthetic checks cover
caption/body metric repetition, date-only and title-only queries, hidden cells,
determinism, unchanged table scores/reads, body-only ordering, and recovery of a
candidate outside v2's returned eight. The four real development cases will run
only after this implementation and protocol are committed. No generalization
claim or default promotion is planned from those inspected cases.
