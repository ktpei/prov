# Financial evidence retrieval: findings and next test

## Saved-result diagnosis

The compact-response assessment measures exact frozen evidence-location packets,
not exhaustive semantic support. Its 1/6 five-read result must not be read as proof
that the other five responses contain no useful or equivalent evidence. The
[post-hoc diagnosis](assessments/financebench-compact-read-v1/retrieval-gap-diagnosis.json)
uses saved responses, questions and frozen packets only; it introduces no new
searches, rankings, reads, packet alternatives or successes.

| Case | Frozen-location gap in the saved five reads |
| --- | --- |
| American Water Works | Operations-statement scope/period/units and operating-income row on page 86 are unmatched; rank 2 contains the cash-flow packet on page 88. |
| Verizon | Balance-sheet packet on page 56 is unmatched. Revenue context is returned, but its selected window stops at L1034 before the L1040 revenue row. |
| Coca-Cola | Neither required statement page 74 nor 76 is selected. Employment-letter matches include instruction words; their causal ranking contribution is unmeasured. |
| 3M | No frozen page-25 role matches, but ranks 1–4 contain relevant segment tables on pages 30–33, including organic sales and adjustment rows. |
| Johnson & Johnson | Required statement pages 46/47 are unmatched; returned material concerns inventory-related costs, returns, pension ratios and employee turnover. |

For 3M, saved rows L1082–1084, L1123–1126, L1163–1166 and L1200–1203 contain
potentially useful distributed evidence outside the frozen locations. The company
row required by the current packet is absent. Whether alternative evidence is
semantically sufficient, and whether every current role is necessary for the
question's interpretation, remains unadjudicated. The M&A-only/organic-growth
ambiguity also remains. Do not silently expand or weaken the frozen packet to
credit this result; a separately versioned, independently reviewed alternative
assessment would be needed. This limitation matters before interpreting a new
retriever's location score as an answer-quality improvement.

## Primary research reviewed

**Structure plus terminology.** FinGEAR combines financial term-to-SEC-Item guidance,
hierarchical within-Item retrieval and cross-encoder reranking. It motivates
source-derived statement context and careful distinctions between financial
metrics, but its combined architecture does not isolate a benefit from synonyms
alone. Its training/evaluation setup also cannot be treated as a ready-made
uncontaminated model for this repository. [FinGEAR](https://aclanthology.org/2025.findings-emnlp.382.pdf)

**Page-level retrieval is distinct from document discovery.** A FinanceBench study
trains a page scorer with document-grouped five-fold evaluation. It improves 10-K
page recall while underperforming its baseline on 10-Q, 8-K and earnings documents.
Gold pages train the scorer, so model adoption would require a training-overlap
audit. Page recall is also weaker than complete evidence or financial correctness.
[Decomposing Retrieval Failures](https://arxiv.org/html/2602.17981v1)

**Structural chunks motivate an ablation, not an assumed win.** Financial Report
Chunking preserves table/title structure and uses enriched indexing representations.
Its comparisons also change parsing and representations. It evaluates 141 of the
150 questions after recovering 80 documents, illustrating why our own acquisition
failures must remain in the denominator rather than become silent exclusions.
[Financial Report Chunking](https://arxiv.org/html/2402.05131v3)

**Decomposition does not guarantee complete support.** The decomposition study
retrieves subquestions and reranks their union. Its HotpotQA discussion reports a lower supporting-fact score:
17.9 with decomposition plus reranking versus 19.6 for reranking alone,
despite improved answer/retrieval metrics elsewhere. Candidate pools and costs also
differ. We should preserve complete-support measurements and matched accounting,
not infer that more generated subqueries necessarily improve the harness.
[Question Decomposition for RAG](https://aclanthology.org/2025.acl-srw.32.pdf)

**Relationships between evidence sources can matter.** Join-aware table retrieval
considers both query–table relevance and relationships between tables. This is
relational-table research, not evidence that the same method improves PDF finance
questions. It supports preserving entity/period/unit compatibility and complete
alternatives instead of rewarding isolated plausible operands.
[Join-Aware Multi-Table Retrieval](https://aclanthology.org/2024.acl-long.148.pdf)

## Proposed next experiment — prototype implemented, assessment not executed or frozen

Our inference from these findings is to test one source-page ranking signal before
adding a query planner. Keep original questions, declared documents, native text,
parent windows, compact read metadata and context policies fixed. Score all eligible passages and retain up to 25 positive-score BM25 candidates
in both conditions. Control selects its first five; challenger
reranks that same pool using equal reciprocal-rank contributions from passage and
containing-page BM25 with constant 60 and deterministic ties. No page filter,
generated text, synonym expansion, inferred formulas or label-derived query terms.

Both conditions compute the same score sets and preserve one question, two local
scoring passes, up to 25 retained candidates, at most five parent reads and the 32K context budget.
Record actual compute/runtime and response sizes; equal caps are not equal cost.
Page text used in ranking receives no delivered-evidence credit unless returned.
Freeze code, all parameters and provenance before searches, then replay before
packet grading. Report candidate-pool opportunity, delivered and retained frozen
packet coverage, paired regressions, operational failures and all-six denominators.
Also report the known incompleteness of location annotations; do not silently score
potential alternatives as false financial answers.

Before development results, reserve separate validation groups from metadata only,
preserving existing partition membership and excluding exposed issuers/cross-suite
aliases. Freeze the final policy before opening those questions or labels. Do not
replace unavailable sources or tune from validation. Any future planner must accept
only question, permitted source metadata and a separately frozen terminology
resource; evaluator roles, gold pages, reference formulas and reference-derived
operand lists must not enter its inputs or examples.

## Incidental research exposure

Primary-paper excerpts exposed a FinanceBench example from `VERIZON_2021_10K`
(`financebench_id_00859`) and an `AMCOR_2020_10K` net-receivables example. Both
document groups are now registered as development exposures. Metadata-only
projection of the pinned release confirms those document names; it did not inspect
additional questions/references. The Amcor excerpt did not supply a task ID, so no
question-level identity match is claimed. Future selection must exclude these
issuers from untouched-validation claims. No source-document retrieval or paid
model call was made for this research.


## Prototype verification and remaining gates

`provenance/page_ranking.py` implements a local, single-document experiment only;
it is not exposed as an agent tool and does not change the default retrieval
policy. It reuses the existing unrounded passage ranking and hit construction.
Pages are assembled from unique source lines, with metadata appended once per
page. Page BM25 has its own collection statistics across every physical page.
Only positive-scoring pages receive ranks; zero-score pages remain in collection
statistics and contribute no reciprocal rank. Score ties use source/page identity;
fusion uses exact fractions and breaks ties by original passage rank. Missing,
non-integer, unordered, incomplete or cross-page candidate mappings fail explicitly.

All ranking diagnostics are separate from returned hits. Page text used for ranking
is not evidence delivered to the agent. The method cannot recover passages outside
the candidate pool or repair a passage boundary. Both conditions score all passages
and pages; the 25 limit bounds retention, not scoring work.

Verification: seven synthetic tests passed, and ten synthetic default search
responses (both legacy and BM25 versions) were byte-identical to commit `495f901`.
No cohort query, candidate-pool inspection, PDF acquisition or paid call was made.
Independent review also verified thirty synthetic default response comparisons.
A frozen six-response pre-refactor fixture is now checked by the test suite.
Full lint and all 353 tests pass. A metadata-only validation reservation and a
hash-bound assessment protocol must precede any development comparison.
The runner must fix Python hash seed before process startup because baseline query
terms retain set iteration and floating-point summation order; this prototype does
not change that historical behavior. Physical-page identity is trusted from the
verified corpus mapping; this scorer does not independently inspect PDF contents. A separate
[incomplete-judgment review](incomplete-judgments-research-2026-11-16.md) specifies
how to audit equivalent evidence without rewriting the original scores.
