# Statement-context retrieval — fixed development comparison

The prior component experiment is retained unchanged. Its inspected Walmart
failure motivates a second, explicitly targeted development comparison, not an
unseen test. Do not modify queries after the first real run. No default promotion
will follow from these three tasks, regardless of outcome.

## Diagnosis before implementation

[Passage counts](length-diagnostic.json) and independent code inspection do not
support the suspicion that numeric-heavy statements were penalized by length.
The main income/balance passages have 238/200 indexed tokens versus 379.44 average;
most saved first hits are longer. Main target passages retain their headers,
periods and units. Some overlapping continuation windows do not, but that does
not explain why the complete passages were missed. Repeated words in competing
passages remain a diagnostic observation, not a proved cause of rankings.

The previous component plan preserved the full original question but dropped
its explicitly requested statement context from component searches. This
comparison changes only those terms; no BM25, passage, merge or budget change.

## Question-only context policy

Keep the original question and all four component searches. When the question
explicitly names balance sheets or statements of financial position, append the
fixed balance-sheet alias terms to AP and inventory components. When it names
P&L, profit and loss, income statements, statements of income or statements of
operations, append fixed income-statement alias terms to the cost-of-sales
component. The purchases component stays unchanged. Append only question-derived
years as before. Validate every generated query against the 500-character limit
before any search.

A small conservative list of negation/exclusion cues disables all context
additions, including “not”, “without”, “avoid”, “rather than” and “instead of”.
This is not a natural-language constraint parser or a hard statement filter.
Original questions remain intact; unsupported questions use the prior plan.
Alias tokens can match subtotals or narrative text and do not prove statement
identity, source support, period, units, consolidation scope or operand roles.

[IFRS educational Module 4](https://www.ifrs.org/content/dam/ifrs/supporting-implementation/smes/module-04.pdf)
identifies statement of financial position/balance sheet terminology. SEC guides
identify [income-statement/P&L](https://www.sec.gov/files/income-statement-building-blocks.pdf)
and [statement-of-operations](https://www.sec.gov/files/reada10k.pdf) terminology.
The [SEC financial-statement guide](https://www.sec.gov/about/reports-publications/beginners-guide-financial-statements)
distinguishes balance-sheet stocks, income-statement flows and cash-flow
adjustments. These aliases supply retrieval vocabulary, not accounting conclusions.

## Frozen comparison

Run the existing component policy once as baseline and the statement-context
policy once as challenger. Both use the same three exposed tasks, four annotated
page keys, declared-document scope, seven total searches (five for Walmart),
five candidates per query and five final passages. Round-robin merging and all
source bytes stay unchanged. Verify baseline exact replay of the previous result.

Record all task outcomes, paired top-1/3/5 page coverage, whole-task coverage,
complete query traces, candidate pools and input/runtime hashes. No model calls,
source-read calls, OCR, replacement tasks, hidden retries or post-result query
changes. The frozen bundle's known Ulta period-convention issue remains disclosed;
its original labels and scores are not rewritten. This is page coverage only,
not answer accuracy or semantic evidence sufficiency.
