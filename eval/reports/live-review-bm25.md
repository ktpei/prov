# Final live development iteration review

Reviewed all nine reports in `runs/acceptance-2026-11-07-bm25` against the frozen
company documents and unchanged `cloudflare-full-docs-v2` benchmark. This review
was performed by a separate coding agent, not an independent human evaluator.
No paid calls or benchmark edits were made by the reviewer. The batch followed
inspection of earlier development outcomes and changes to retrieval and runtime
instructions. It is another development iteration, not heldout validation.

Five of nine runs delivered validated final answers. Three pass the current
mechanical pre-grader. Those are execution and mechanical counts, respectively;
neither is an independently reviewed overall task-success rate.

| Task | Outcome | Evidence and substantive assessment | Grading limitation or remaining issue |
|---|---|---|---|
| packet-01: revenue | Completed; mechanical fail | Filing L926-L928 supports revenue of 430,082 USD thousand, converted correctly to 430.082 USD million; prose also gives rounded 430.1 million. | Higher precision is valid for the question, which asks USD millions without specifying decimal places. Gold is exactly 430.1 with zero tolerance and requires release anchors although the question permits original evidence. These are reference precision/source overconstraints, not a wrong financial answer. Cited table rows omit the preceding date headers, weakening standalone period inspectability. |
| packet-02: gross margins | Completed; mechanical pass | Release L51 explicitly supports GAAP 77.7% and non-GAAP 78.8%; actuals and accounting bases are distinguished. Additional profit amounts and exclusions are present in release text/reconciliation. | Response adds facts beyond the question, increasing citation burden, but no invented requested metric or basis error was found. |
| packet-03: guidance | Completed; mechanical pass | Release L58-L59 and transcript L251-L252 support lower 451 and upper 452 USD million for Q4 2024. Answer clearly identifies forecasts. | Final quotes are contiguous exact source text, correcting the initial iteration's ellipsis failure. Additional 25% midpoint growth is supported by the cited transcript. |
| packet-04: decline drivers | Stopped: tool-call limit | By tool four, transcript L60-L100 and L200-L240 already contained low churn plus all three management-attributed drivers. | Eight subsequent tools consumed the remaining budget without a final answer. No qualitative success can be claimed. This is evidence-sufficiency/stopping failure, not missing extraction or retrieval. |
| packet-05: definition plus drivers | Completed; mechanical pass | Filing L831 supports same-cohort definition and exclusions. Transcript L211-L215 supports slower larger-customer expansion, pool-of-funds effects, and anniversarying price increases; L71 supports low churn. | Required synthesis is supported. Answer adds prior-year rates, ACV mix, and an outlook; these are in the source, but make an already long answer harder to review. Driver citation spans contain the full support even when the short quotation includes only its opening portion. |
| packet-06: basis reconciliation | Stopped: model-call limit | Read transcript L47-L58 for the non-GAAP disclosure, release L225-L245 for both margin bases, and L328-L333 for the definition. | Evidence was sufficient, yet the agent continued searching and delivered no final answer. This task completed in the initial iteration but not this one; do not describe uniform improvement. |
| packet-07: free cash flow | Completed; mechanical fail | Definition and limitations are financially supported by filing L804/L807. Additional release-based calculation 104.727 - 50.203 - 9.245 = 45.279 USD million is correct. | The question explicitly requests the release; the answer cites the filing for the requested definition/limitation. Unlike packet-01's source-flexible question, this is a real source-instruction mismatch. A release-cited numerical calculation does not replace release evidence for the requested explanation. One repair attempt preceded the validated final answer. |
| packet-08: absent future actual | Stopped: tool-call limit | No final answer was delivered. The question's cutoff and document dates could have supported scoped abstention. | Twelve tools were consumed instead. Do not score this as successful abstention or assume the unreturned answer would have been correct. |
| packet-09: deck date boundary | Stopped: tool-call limit | Deck L1-L40 contains the May 30, 2024 cover date; release L42-L80 includes the later publication and quarter dates. Both were read by tool six. | Further searches/reads, including repeated cover and release reads, led to the cap without an answer. Again this is stopping after sufficient evidence, rather than inaccessible deck text. It does not validate chart interpretation. |

No completed final answer failed literal quote/read validation. That structural
success does not prove every claim's cited span includes its metric's period,
units, or table headers, nor does it enforce source-specific instructions.
The reader supplies full cited spans: a short exact quote can validly be only a
portion of that span, but the complete attached claim still needs support within
its cited evidence. Broad qualitative claims remain subject to human review.

## Cost, context, and reproducibility

| Task | Model calls | Tools | Cumulative input tokens | Accounted USD |
|---|---:|---:|---:|---:|
| packet-01 | 3 | 3 | 7,689 | 0.0030927 |
| packet-02 | 4 | 5 | 16,842 | 0.0064422 |
| packet-03 | 3 | 4 | 7,672 | 0.0031692 |
| packet-04 | 7 | 12 | 37,231 | 0.0122481 |
| packet-05 | 5 | 7 | 23,880 | 0.0093888 |
| packet-06 | 10 | 11 | 46,535 | 0.0150561 |
| packet-07 | 4 | 4 | 20,397 | 0.0087375 |
| packet-08 | 6 | 12 | 19,296 | 0.0069444 |
| packet-09 | 8 | 12 | 49,013 | 0.0162915 |

The nine-task batch used 228,555 cumulative input tokens and 10,670 output tokens,
with settled aggregate cost $0.0813705 and no uncertain-cost flags. Input tokens
are summed across turns, not unique evidence size. No tool errors occurred in
this batch. All traces record `bm25-v2`, the requested OpenRouter model, four
matching source hashes, and frozen-corpus mode.

For the same five tasks as the initial batch, cumulative input fell from 298,881
to 118,423 tokens and settled cost fell from $0.0981087 to $0.0405105. Each batch
completed two of that shared five, with a different pair completing. Retrieval,
instructions, and runtime repair behavior changed together, so this comparison
does not isolate BM25's causal effect or show improved end-to-end reliability.
The independent fixed-query diagnostic improves from 5/8 to 6/8 retrieval anchor
tasks under the same benchmark, while extraction anchor coverage remains 8/8.
Anchor presence still does not establish table/chart correctness.

The strongest remaining issue is bounded research completion: four tasks stop
without answers, including three that visibly read sufficient evidence. The
system reliably enforces limits; it does not yet reliably decide when to answer
or abstain. Improvements to sufficiency checks, context pruning, finalization,
and model/tool behavior need a new recorded development iteration. Preserve
both current iterations and their failures. A later credible evaluation should
use newly authored, uninspected tasks and independent semantic review.
