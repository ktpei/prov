# Bounded reads deliver evidence that search snippets omit

The three frozen conditions all delivered complete annotated evidence for 1/3
cases after one read and 2/3 after three or five reads. Their original snippets
covered 0/3 complete packets at every cutoff. Reading realized the existing parent
opportunity; it did not improve retrieval ranking or establish answer accuracy.

Implementation `ec9023d`, freeze `4171bcd`. The [plan](plan.md), condition protocols,
projected plans, separate grades and [receipt](receipt.json) preserve inputs and
outcomes. Raw deterministic results/journals are under the corresponding ignored
`runs/bounded-reading-2026-11-16/` directories, bound by receipt hashes.

| Condition | Complete @1 | Complete @3 | Complete @5 | Text chars @5, all 3 cases | JSON bytes @5, all 3 cases |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original question | 1/3 | 2/3 | 2/3 | 48,720 | 91,173 |
| DPO components | 1/3 | 2/3 | 2/3 | 52,897 | 95,839 |
| Statement context | 1/3 | 2/3 | 2/3 | 52,224 | 95,166 |

Each condition made 15 original reads (five per task). All **45 original reads**
succeeded without truncation. Separate verification made **45 replay reads**;
these are verification work, not hidden retries or additional policy decisions.
Search replay and projection preflight also occurred, with no query changes.

- Ulta's first read contains the complete five-role packet in a single response.
- NIKE needs a union of responses: three reads cover all five roles, but no single
  response contains the whole packet. The period/scale and operating/financing
  totals missing from snippets are delivered by reads.
- Walmart remains incomplete at every cutoff. Reading selected passages cannot
  supply the required income/balance statement evidence absent from those hits.

For every case/cutoff/role, returned-read coverage equals parent opportunity.
Prefix coverage is nondecreasing. At top five, the original condition requests
417 lines and returns 393 unique lines across the three distinct source documents;
the variants request 428 and return 404 unique lines. Each has 24 repeated lines.
Gross delivery costs count repeated text; unique coverage does not. Neither query
variant improves coverage, and both deliver more text than original-question
retrieval. No policy is promoted from these three exposed development cases.

## What this result does and does not establish

This verifies actual tool-response evidence delivery, with unchanged posthoc
coding-agent packets. It does not validate semantic sufficiency, column
association, calculations, model reasoning or annotations. The Ulta FY2023 versus
company fiscal-2022 reference convention remains unresolved. No original scores,
source bytes or holdout boundaries changed. Human financial validation is pending.

The runner's search replay uses existing reference-aware diagnostics. The reader
receives only replay-verified source/range projections, and packet labels are
opened only after exact result and journal replay. This is narrower than claiming
the entire runner never sees benchmark references.

The baseline does not simulate the agent's 32K model-context projection. At top
five, canonical response JSON bytes exceed 32,000 for NIKE and Walmart; bytes are
not directly interchangeable with the agent's character-budget accounting. Thus
successful tool delivery must not be described as complete model-visible context.
Testing that projection is a remaining assessment question before full-agent use.

All 295 tests and lint pass. Independent implementation review covered forged
reports/plans, changed inputs, extra/altered journals, interruption and failed or
empty rank slots. There were no paid inference calls; cumulative conservative
spending stays $0.4814193. Default agent behavior remains unchanged.

Independent saved-artifact review recomputed counts, per-case budgets, overlaps
and single-response results; all protocol, source, prepared, run, journal and grade
hashes agree. That review did not perform additional retrieval or read calls.

Follow-up: the separately frozen [context-retention experiment](../context-retention-2026-11-16/report.md)
now measures the previously untested projection and finds evidence loss at five
reads. It does not alter this tool-delivery result.
