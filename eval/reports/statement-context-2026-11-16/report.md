# Statement-context retrieval: unchanged final coverage, weaker candidate pool

Implementation `b8cff7f` and [protocol](protocol.json) were committed before the
run (`9a0cc40`). Both conditions completed once, each using seven searches over
the same three exposed development tasks. The previous component policy replays
exactly. [Receipt](receipt.json), [comparison and candidate diagnostics](summary.json).

Both conditions reach **2/4 annotated pages at top-1, top-3 and top-5**, with
**2/3 tasks having complete annotated-page coverage**. There are zero paired
wins, zero losses and three ties on final top-five page coverage. Nike and Ulta
remain unchanged. No default policy is promoted; no paid inference occurred.

The statement-context terms did not rescue Walmart's missing pages. Its baseline
AP query includes physical page 59 at rank five, but the new AP query excludes it
from its five candidates. Physical page 57 remains absent from all candidate
lists. Thus expected Walmart pages in the union of candidate lists fall from
**1/2 to 0/2**, even though the final-coverage metric stays unchanged. Candidate
regression must not be hidden behind the unchanged headline metric.

This outcome follows a separate negative diagnosis: the main required statement
passages were not unusually long and already retained title, units and years.
[Measured passage lengths](length-diagnostic.json) do not support blaming numeric
content or missing primary-passage headers for the observed misses. Lexical term
repetition in competing passages is an observation, not a demonstrated causal
explanation or a license to tune a source-specific rank boost.

The new policy preserves requested statement-family vocabulary but remains
ordinary lexical retrieval, with no verified statement classification. It can
still retrieve narrative discussions, subtotals, or the wrong statement. This
three-task, iteratively inspected experiment does not establish general behavior.
The frozen input's known Ulta fiscal-year convention issue remains disclosed;
original questions, references, scores and corpus bytes are unchanged.

Lint and all 271 tests pass. Future work should evaluate candidate granularity or
structured evidence retrieval under a new protocol and broader evidence, rather
than continuing to add aliases to this same inspected case. Both negative runs
remain preserved and the default graph/retrieval stays unchanged.
