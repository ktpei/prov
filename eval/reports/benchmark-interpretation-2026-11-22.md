# Interpretation of the November benchmark results

Prepared November 22, 2026, from the runs completed November 20, 2026.

**The strongest finding is that the current web research workflow struggles to obtain usable evidence.** Performance was encouraging on the small CFA and TAT-QA samples, but FinQA also exposed errors when documents were already supplied. The evidence supports improving document navigation and financial answer checks before treating the system as a dependable autonomous research assistant.

| Benchmark | What this run tested | Observed result |
|---|---|---|
| Daloopa quick | Finding financial figures through web search and document reading | Frozen score: 3/25 exact, 6/25 within 1%. After one confirmed reference-sign correction: 4/25 exact (16%), 7/25 within 1% (28%). |
| CFA-Easy | Financial knowledge and reasoning through multiple-choice questions | 5/5 correct choices (100%). |
| CFA-Challenge | More difficult financial reasoning through multiple-choice questions | 4/5 correct choices (80%). |
| FinQA | Numerical answers using supplied financial documents | 2/5 scorable cases correct (40%); one additional selected case had an unresolved reference. |
| TAT-QA | Answers using supplied tables and text | 4/4 exact matches (100%); all four scales matched. |

These results come from the [Daloopa run report](daloopa-quick-2026-11-20/report.md) and [existing-suite run report](external-quick-2026-11-20/report.md). The benchmarks measure different tasks and should remain separate rather than being averaged into a single accuracy score.

**Daloopa primarily reveals a coverage problem.** Of 25 attempted questions, eight produced numerical answers, twelve ended in abstention, and five stopped or failed. Thus, only 32% of questions received a numerical answer. Trace inspection found repeated searching without reading, partial reads that did not reach the relevant table, and execution limits reached before evidence could be gathered. Two attempts hit the document-context limit, two hit the model-call limit, and one failed at the output-length limit.

After the reference correction, seven of the eight numerical answers were within 1% of the expected value. That conditional success rate of 87.5% is useful for diagnosis, but excludes the seventeen unanswered cases. The appropriate overall tolerance result remains **7/25, or 28%**. Abstaining can avoid unsupported claims, but a workflow that leaves most questions unanswered still provides limited research coverage.

**Exact matching and financial correctness are not identical.** Three answers passed tolerance but failed exact matching because the model and reference used different precision. For example, iRhythm's answer was 13.677 million against a reference rounded to 13.7 million. Conversely, SBI's answer used nine-month cumulative earnings per share when the question requested a standalone quarter. That is a substantive period error. The evaluation should retain exact and tolerance scores while separately checking period, metric, unit, and source support.

The Discover case exposed a scoring defect: preparation dropped a minus sign from a formatted reference. The model's negative answer agreed with the publisher wording and captured source. Correcting that reference raised exact matching from 12% to 16% and tolerance matching from 24% to 28%. This was a correction after the run, not a model improvement. Original scores remain preserved, and no question was rerun to obtain the adjustment. Coding-agent inspection supports the diagnosis; independent human financial validation has not established supported accuracy.

**The existing suite shows uneven performance even without web retrieval.** The CFA results suggest useful financial knowledge on the sampled questions, and TAT-QA suggests the model can extract answers from the supplied tables and text. FinQA prevents a broader claim that supplying evidence solves the problem: its five scorable cases contained two correct answers, two incorrect numerical answers, and one output-length failure. This warrants separate review of calculation setup, numerical reasoning, and response completion. The sixth selected case was not attempted because its reference remained unresolved; it was not counted as a model failure or silently replaced.

**These are development signals, not production accuracy estimates.** Each existing-suite sample contained only four to six questions. Daloopa used a fixed, category-balanced sample of 25 public questions with parseable references, rather than a random sample of the entire dataset. The questions are exposed development material, and the evaluation used adapted conditions: FinQA measured scalar answers rather than official program accuracy, while TAT-QA retains annotation caveats. Differences between these tasks cannot isolate the causal effect of retrieval. Our Daloopa results are also not directly comparable with its published web-app/MCP leaderboard.

The Daloopa run used an estimated **$1.22** in model and search costs, 134 model calls, and about seven minutes of summed task runtime. The existing suite cost approximately **$0.024**. These estimates describe this bounded configuration; they do not establish full-suite cost or production latency. The lean limits may have constrained completion, but simply increasing them has not been shown to improve accuracy.

**The next experiment should improve evidence access under a controlled comparison.** Keep the same development questions and scoring policy, add targeted navigation to relevant document sections, and measure whether more questions receive correct, supported answers. Report answer coverage, exact and tolerance matching, abstentions, execution failures, and cost together. Review period and metric alignment explicitly so improved completion does not merely produce more plausible but incorrect numbers. Treat any rerun on these exposed questions as development progress, then verify gains on appropriately protected evaluation material under a frozen protocol.

The full Daloopa inventory remains available but has not been run. It contains 500 questions: one reserved case, 426 currently parseable references, and 73 requiring reference review. Full mode can execute the 499 nonreserved questions while retaining unresolved cases as unscored. A broader run would improve visibility into failure patterns; reliable interpretation still depends on resolving reference quality and preserving those denominators.
