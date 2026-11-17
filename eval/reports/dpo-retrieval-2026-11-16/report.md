# DPO component retrieval: no coverage improvement

Implementation `a55ff94` and [protocol](protocol.json) were committed before the
run (`6d9837d`). Both conditions completed once, with unchanged three-task/four-page
denominators. The original-question baseline replays the saved document-scoped
report exactly. [Receipt](receipt.json), [full comparison](summary.json).

| Metric | Original question | Component challenger |
| --- | ---: | ---: |
| Search calls | 3 | 7 |
| Top-1 annotated pages | 2/4 | 2/4 |
| Top-3 annotated pages | 2/4 | 2/4 |
| Top-5 annotated pages | 2/4 | 2/4 |
| Top-5 complete page coverage | 2/3 tasks | 2/3 tasks |

There are zero paired wins, zero losses and three ties. Nike and Ulta receive
one unchanged query each and retain coverage. Walmart receives five searches
but still misses both required pages in the final five passages. No default
promotion follows. No paid inference or source reads were added.

The saved traces explain two distinct problems. The accounts-payable component
finds Walmart's physical page 59 at rank five; the round-robin merge takes the
first hit from each query, so that page is absent from the final five. Physical
page 57 is absent from every component's five-hit candidate list. Thus changing
the merge alone cannot recover the full evidence set from this candidate pool.
No additional searches were run to reach this diagnosis.

This is a targeted experiment on previously inspected development tasks, with a
larger search budget, not a broad accuracy test. Page coverage does not establish
snippet contents, correct operand roles, source support or a correct answer.
The frozen bundle predates Ulta's fiscal-year convention review flag; that known
issue remains disclosed, with no retrospective gold or metric changes.

The default retrieval policy, original source corpus and original 25-task suite
remain unchanged. Lint and all 270 tests pass. Future retrieval changes must
address both candidate generation and selection under a new recorded experiment;
this result must not be overwritten or presented as an improvement.
