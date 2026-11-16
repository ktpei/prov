# Complete evidence components versus page hits

All three saved retrieval conditions replayed exactly before labels were opened.
The same three exposed development cases remain in every denominator. Frozen
[plan](plan.md), [packets](packets.json), condition protocols/results and
[receipt](receipt.json) preserve the experiment. Implementation `f5954bb`,
protocol freeze `3ec598a`; no model calls, new source reads, OCR or source changes.

| Condition | Parent complete @1 | Parent complete @3/@5 | Snippet complete @1/@3/@5 |
| --- | ---: | ---: | ---: |
| Original question | 1/3 | 2/3 | 0/3 |
| DPO components | 1/3 | 2/3 | 0/3 |
| Statement context | 1/3 | 2/3 | 0/3 |

These are complete annotated role-line packets, not page hits or financial answer
scores. Parent passages provide an opportunity for later reads; their complete
contents were not returned in search snippets. Results are identical across the
three conditions; existing page-coverage and benchmark scores remain unchanged.

- Walmart: no required packet role is completely covered in the five selected parent passages
  or snippets. Neither retrieval variant fixes the underlying miss.
- NIKE: all required headers, period/scale and three cash-flow totals are present
  in the union of the first three parent passages, but no single parent contains
  the whole packet. Snippets completely cover the investing-total role only; they lack complete coverage of the
  statement identity, period/scale, operating total and financing total.
- Ulta: the first parent passage contains the complete packet. Snippets completely cover
  the absolute-versus-relative SG&A role, but lack complete coverage of the annual-period heading
  and complete percentage comparison, driver and offset spans. The known fiscal
  year convention issue remains unresolved (`reference-d00daa9a06589412`).

The result motivates evaluating bounded reading after search, with its own fixed
budget and replayable policy. It does not establish that an agent cannot answer:
this experiment tests saved search output, not the agent's subsequent reads.
It also does not prove the annotations are exhaustive, alternative evidence is
absent, or the numbers are associated with the correct columns. These are posthoc
coding-agent annotations on three inspected public development tasks, not human
validation or generalization evidence. See the plan for adjacent-text exposure.

Integrity review found and fixed missing end-of-run raw hashes for prepared files
and corpus binding before freezing. Mutation tests now reject changes to each of
those four files without writing a result. All 278 tests and lint passed; seven
focused tests cover empty snippets, exact source slices, complete alternatives,
fixed denominators, replay-before-labels, forged reports and input mutation.
No defaults were promoted and no paid spending was added.

Independent review recomputed all counts and verified frozen packet/protocol/result
hashes. Incomplete roles can still contain partial evidence.
