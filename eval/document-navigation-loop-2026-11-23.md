# Document ingestion and navigation improvement loop

Status: implementation and synthetic verification; live comparisons pending.

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
