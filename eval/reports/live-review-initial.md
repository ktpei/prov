# Initial live development review

Reviewed the five reports in `runs/acceptance-2026-11-07-v2` against the frozen
Cloudflare documents. This is an engineering review by a second coding agent,
not an independent human review, a heldout score, or evidence of generalization.
No paid calls were made by the reviewer and no benchmark settings, keys, or
queries were changed after inspecting these live results.

| Task | Runtime outcome | Substantive assessment | Mechanical interpretation |
|---|---|---|---|
| packet-01 | Completed | Requested Q3 revenue, 430.1 USD million, is supported by release L50. Added exact table revenue and prior-year comparison are in the source. | Valid trace and quotes. Numeric check fails because returned period is `Q3 2024 (three months ended September 30, 2024)` rather than exact canonical `Q3 2024`; this is a period-string false negative, not a wrong reporting period. |
| packet-03 | Failed quote validation | Draft endpoints 451 and 452 USD million and forecast interpretation are supported by release L58-L59 and transcript L251-L252. | Failure is legitimate under the exact-quote contract: several quotation strings insert literal `...` between nonadjacent phrases. This is not a valid completed answer despite correct draft numerical content. |
| packet-04 | Stopped at spending reservation limit | Evidence read includes the CFO's drivers, but no final answer was delivered; cannot score qualitative task success. | Two reads requested more than the 80-line maximum and were retried. Later cumulative context made the next conservative reservation unaffordable even though settled cost was only about $0.0197. |
| packet-06 | Completed | Core reconciliation is supported: call L53 sets adjusted non-GAAP basis; release L239-L240 distinguishes GAAP 77.7% from non-GAAP 78.8%. Added gross-profit reconciliation values are present. | Valid trace and literal quotes. Anchor coverage falsely fails on table serialization `77.7 | %` / `78.8 | %` versus contiguous-percent regexes. Do not change this benchmark retrospectively; record the limitation and manual review. |
| packet-08 | Stopped at tool-call limit | No completed abstention. A future full-year actual result cannot be established from the packet's 2024 cutoff, but the agent kept searching forecast/target terms. | Genuine execution failure for the requested task, not abstention success. Twelve tool calls were consumed. |

There is a narrower citation-support issue in packet-06's extra detail:
`call_gross_margin_comment` says prior-year margin was 78.7% but cites only L76,
which ends before L77's 78.7% statement. Another separate claim cites the release
for the prior-year number, so the fact exists in the corpus; nevertheless this
particular claim's cited span is incomplete. Literal quote presence alone does
not prove that the whole attached claim is supported. Table-row citations also
need date/column-header context to make accounting periods inspectable.

The two completed answers include substantial extra facts and computations beyond
the question. This increases response length, citation requirements, and review
burden without improving the core answer. The evidence for packet-01's requested
answer was already read after three tools; seven more calls followed. The central
packet-06 distinction was already available after four tools; six more followed.

## Context and spending

| Task | Model calls | Tool calls | Cumulative input tokens | Output tokens | Accounted USD |
|---|---:|---:|---:|---:|---:|
| packet-01 | 6 | 10 | 64,177 | 1,290 | 0.0208011 |
| packet-03 | 4 | 6 | 33,808 | 1,216 | 0.0116016 |
| packet-04 | 8 | 11 | 62,181 | 870 | 0.0196983 |
| packet-06 | 6 | 10 | 68,004 | 2,333 | 0.0232008 |
| packet-08 | 7 | 12 | 70,711 | 1,328 | 0.0228069 |

Input tokens are summed across model requests, not unique evidence tokens. Each
search returned roughly 6.4–7.2K serialized characters; repeat searches accumulate
in conversation history. Some reads returned 14–21K serialized characters.
Packet-08 used eleven searches and only one completed read, returning about 79K
characters across tools. Context selection and stopping behavior are therefore
material bottlenecks despite bounded individual tools.

All five runs record the requested model, four matching source hashes, and
`frozen_corpus` mode. Experiment metadata explicitly records a dirty working tree
at the starting Git revision, so that revision alone is not a reproducible code
snapshot; preserve the reports with the implementation commit. Settled aggregate
cost is $0.0981087, with `cost_uncertain: false` in these five reports.

Useful generic development changes are to prefer narrow reads at returned passage
locations, avoid repeated equivalent queries after sufficient evidence is read,
stop after obtaining the requested evidence, copy contiguous literal quotes,
include necessary table/date headers, and use packet-date boundaries for future
actuals. Canonical reporting-period formatting can improve machine grading, but
should not conceal the period-equivalence limitation in the initial results.
Any rerun after such changes is a new development iteration on already-inspected
tasks. Keep both iterations and do not present the second as heldout performance.
