# Document ingestion and navigation improvement loop

Status: first quick comparison complete; second treatment and full comparison in progress.

The November 20 pilot exposed inaccessible document tails and repeated discovery
without targeted reading. The baseline requests only 16,000 characters, and web
documents never enter the local passage index. This is an acquisition/navigation
limitation before it is a model reasoning problem.

## Research and decisions

Primary sources checked November 23, 2026:

| Source | Evidence and justified application |
|---|---|
| [CORE](https://arxiv.org/abs/2611.07859), November 5, 2026 | Coarse-to-fine retrieval, short snippets, source expansion and duplicate suppression improved controlled closed-corpus research benchmarks. Adapt the navigation pattern with simple lexical ranking; this is not a replication of its dense retriever/reranker. |
| [FinFIRST](https://arxiv.org/abs/2609.25192), September 21, 2026 | Separates financial acquisition, source verification and calculation/answer formation. Preserve separate outcome and evidence measures; numerical proximity is not supported financial correctness. |
| [LiveSearch](https://arxiv.org/abs/2610.37166), October 27, revised November 9, 2026 | Time-dependent search results can change task outcomes. Keep run dates and captured evidence, and label live comparisons as system-level evidence rather than isolated causal proof. |
| [BrowseComp-Plus](https://arxiv.org/abs/2508.06600), August 8, 2025 | Fixed corpora address opaque/dynamic web-search confounds. Add deterministic synthetic document regressions alongside live evaluation. |
| [Anthropic tool engineering](https://www.anthropic.com/research/writing-tools-for-agents), September 11, 2025 | Supports concise tool responses, filtering/range selection, explicit boundaries and trajectory-driven iteration. Use a small finder and bounded reads rather than introducing more agents or generated summaries. |
| [Exa contents documentation](https://exa.ai/docs/contents/quickstart) and canonical build-with-exa skill | Use capped text extraction for document navigation, inspect per-URL statuses, retain durable cost accounting. Extraction completeness is not guaranteed by a successful response. |
| [Anthropic agent evaluations](https://www.anthropic.com/research/demystifying-evals-for-ai-agents), January 9, 2026 | Distinguish capability gains from regression controls and combine deterministic checks with calibrated semantic review. Keep per-task transitions and execution failures visible. |
| [ParseBench-2](https://arxiv.org/abs/2611.17400), November 12, 2026 | Parsing evaluation should penalize changed facts and broken structural relations even when most text is recovered. Character coverage alone cannot establish ingestion quality. |
| [Docling serialization](https://docling-project.github.io/docling/concepts/serialization/), current documentation | JSON/HTML preserve table spans that Markdown cannot fully express. Existing native HTML/table infrastructure should be assessed before adding an expensive new parser; structured extraction is a potential next treatment, not an established improvement here. |
| [FinMRAGBench](https://aclanthology.org/2026.findings-acl.187/), July 2026 | Financial evidence can span pages/documents; incomplete retrieval and complex reasoning remain distinct failures. Larger text retention does not restore lost chart/table geometry. |

Finance-paper abstracts were inspected without opening their issuer-specific task
examples. The six FinanceBench reservations and their exposure dispositions remain
unchanged, including prior issuer exposure for Amazon and Microsoft. Other known
reserved issuers remain protected. No reserved content is used for development.

## Versioned treatment

`--navigation baseline` retains the existing behavior. `--navigation document-v1`
adds a source-local lexical finder, immutable cached extraction up to 150,000
characters, and reads of up to 30 lines. The extraction cap leaves room within the
existing 2 MB transport bound even for heavily escaped Unicode. It is a bounded
snapshot, not a promise of the complete original document. A cap flag and explicit
incompleteness accompany navigation and reading.

Finding returns at most three nonoverlapping ranges with short discovery snippets.
Only explicit reads authorize citations. Context projection keeps the latest
navigation result and latest read, so a large earlier search cannot hide a new
finder result. Histories without finding retain their original projection.
Candidate instructions distinguish web discovery from lexical document search and
require checking standalone-quarter versus cumulative periods.

This is a combined ingestion/navigation treatment. Larger extraction, new finding,
shorter reads and prompt guidance change together. A positive result would justify
the bundle, not prove which component caused the gain. Table geometry, extraction
quality and calculation validity remain potential failures to inspect next.

## Frozen comparison plan

1. Run the original fixed quick25 under baseline and candidate with the same
   current prepared references, model, six-call/eight-tool limits, 90-second task
   timeout, 1,800 output-token cap and $0.12 per-task budget. Use $3 aggregate per
   arm. Preserve November 20 results separately; do not compare changed graders.
2. Inspect paired outcomes and traces. Accept a candidate only if numerical
   success improves without a new citation-integrity regression. Record negatives
   and any follow-up policy as separate versions, never overwrite a run or select
   the best of repeated attempts. Keep improvements generic, not issuer-specific.
3. Freeze the chosen treatment, then run baseline and treatment on the full500
   Daloopa inventory (499 nonreserved), with identical references and $60 per arm
   ceilings. Report full results and the remaining474 outside the quick25
   separately. These are public development comparisons, not unseen validation.
   The unchanged baseline may begin earlier from an immutable runtime snapshot;
   it does not depend on quick-run candidate selection.
4. Rerun the complete eligible prepared existing suites as regression controls.
   Record exact counts, reservation exclusions, unresolved references and any
   issuer-identity limitations before dispatch. Navigation is not used by those
   tool-free suites, so changes there cannot be credited to navigation.
5. Compare exact/tolerance results, answer coverage, abstentions, stopped/failed
   attempts, citation quote validity, source acquisitions/finds/reads, cost and
   latency. Semantic support remains unestablished without appropriate review.
   Keep unresolved references out of scored denominators but in inventory.

All runs use `deepseek/deepseek-v4.1-flash-1017`, the prior model, with conservative
token rates of $0.60/$2.40 per million. One attempt per question per policy, no
automatic retries. Stop on uncertain billing. Protocol and implementation hashes
are recorded before inference. Full-run per-arm ceilings are conservative bounds,
not predicted charges. Live source changes and model nondeterminism remain
confounders; synthetic tests isolate access and citation behavior.

The loop ends this round with a measured decision and a saved report. It does not
silently consume reserved evaluation content or keep rerunning until scores look
better. A new hypothesis follows a documented failure analysis and a new policy.

## Execution notes

Lint and 636 tests passed for the initial navigation implementation, including
synthetic access, citation, cache, budget and context-projection checks. A separate
read-only review identified and verified fixes for latest-finder context omission
and character-versus-byte transport sizing before measured runs.

The first quick-arm launches stopped on OpenRouter authentication before inference:
an invalid inherited key overrode the valid ignored project key. A read-only key
check returned HTTP 401 for the inherited credential and authenticated the project
credential. Those setup attempts and provisional reservations remain separately
recorded. Measured runs explicitly remove inherited keys so the project settings
apply; this is a setup correction, not best-of answer selection.

Existing-suite metadata audit authorizes 70 prepared CFA-Easy, 30 CFA-Challenge,
97 FinQA (three LMT cases excluded), and the same four already-exposed TAT-QA
controls. The remaining 96 TAT-QA cases have unresolved issuer identities and are
not expanded into. The four repeat controls also do not establish issuer clearance.
These 201 cases cover eligible prepared subsets, not entire publisher releases.
Their frozen metadata protocol records exclusions before dispatch. Tool-free
settings remain unchanged: 2,000 output tokens, 60 seconds, $0.03 task ceiling.

The full baseline uses a copied runtime under
`runs/navigation-loop-2026-11-23/runtime-baseline`; only protection metadata, not
protected issuer source documents, accompanied that copy. The original baseline
implementation is preserved while later candidate work proceeds.

## First measured iteration

The paired quick25 completed with the same references, model and execution limits:

| Measure | Baseline | document-v1 |
|---|---:|---:|
| Exact numerical matches | 4/25 | 9/25 |
| Within 1% | 6/25 | 11/25 |
| Numerical answers | 7 | 12 |
| Quote-valid numerical answers | 7 | 12 |
| Completed responses including abstentions | 16 | 21 |
| Stops/failures | 9 | 4 |
| Estimated cost | $1.0828304 | $0.8561940 |
| Sum of task latency | 409.9 seconds | 409.3 seconds |

Both arms use the corrected current references. The older November 20 baseline is
retained as historical evidence, not substituted for this fresh baseline. All
runtime hashes match the preserved initial runtime snapshot. Exact quote checking
does not establish source/period/metric correctness. The full baseline is running;
no full-suite improvement has yet been established.

## Second treatment and decision rule

Trace review of quick25 found concrete v1 failures: a wider requested read was
clamped before an already-found target row; repeated finds consumed turns without
reading; a rounded narrative answer was retained after a precise table was found
too late to read. These observations motivate `document-v2`, not issuer-specific
special cases.

V2 preserves up to 80 requested lines within a 9,000-character serialized-line
budget, returns continuation explicitly, and shortens discovery highlights to one
700-character excerpt per result. It exposes missing query terms and per-passage
matched terms as lexical diagnostics, not semantic judgments. Guidance prioritizes
reading a promising match immediately and changing source after repeated weak
matches. Larger extraction and exact citation authorization remain unchanged.

Run the same quick25 once under v2 with unchanged model, references, task/time/cost
limits. Compare against both completed arms. Primary selection criterion is
within-1% success, followed by exact success and coverage with no citation-integrity
regression. Preserve all arms, including regressions; do not cherry-pick per-task
answers. Freeze the selected complete treatment for the full comparison.

## Calculation and ingestion diagnostics

Independent coding-agent review found no clear metric/period/unit failure among
v1's nine exact matches. Two tolerance-only answers were supported rounded source
values. One mismatch (Mitsui) remained unresolved against the captured source;
its reference and score were not changed. This review is not human validation.

The previous FinQA misses were inspected before choosing a calculation treatment.
TROW used the right operands but rounded too early. ABMD correctly subtracted the
numbers while the executable reference expected a relative change; the question
does not clearly specify that interpretation, and its human-written answer
conflicts with the executable reference. A calculator cannot resolve that ambiguity.
The new optional `--reasoning precision-v1` keeps the same one-request, tool-free
condition and clarifies answer type, requested periods, units and intermediate/final
precision. It does not encode benchmark-specific formulas or force ambiguous
questions into relative changes. Compare all 201 eligible controls against the
completed baseline once, using unchanged inputs, scorer, budget and token limits.
No reference is changed after observing these predictions.

A separate $0.001 Exa extraction probe on an already-exposed Smurfit Westrock
source used documented `includeHtmlTags` to test whether original table markup
could be recovered cheaply. It returned no table/cell tags. This does not establish
general provider behavior, but provides no basis to claim that toggling that option
restores table structure. It is not included in benchmark scores or adopted by the
candidate. A native structured parser would need a separately tested acquisition
path and geometry validation; it is not added speculatively.
