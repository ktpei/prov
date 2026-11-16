# Broader context validation: preparation status

Selection rules were frozen in `40d24d2`; all six selections were committed in
`aaeb24e` before acquisition or content inspection. Independent review reproduced
the complete 84-group ledger, all exclusions, partition membership and both
selection/preparation orders. The selected companies are Verizon, Coca-Cola,
Costco, Johnson & Johnson, 3M and American Water Works.

| Stage | Verified count |
| --- | ---: |
| Fixed task/source slots | 6 |
| Distinct known companies | 6 |
| Pinned mirror tree entries | 6 |
| Downloaded/verified PDF bodies | 6 |
| Extracted documents | 6 |
| Prepared task/reference records | 6 |
| Annotation-reviewed questions/evidence | 6 |
| Executed retrieval/context cases | 0 |

## Source-inventory research

The related source-ingestion chat researched the pinned repository metadata, and
the lead independently checked the commit-to-tree-to-blob chain through the
[GitHub tree API](https://docs.github.com/en/rest/git/trees?apiVersion=2022-11-28).
The pinned commit resolves to tree `dd439a15cd136001f70afba8b77ac534bd83ce8e`.
[Inventory](inventory.json) records each exact path, size and Git blob identity,
with the commit/tree response hashes. Raw metadata responses are retained locally
under `runs/financebench-context-v1-metadata/`. At that metadata stage no PDF bodies
were fetched; the subsequent frozen acquisition is recorded below.

| Source | Expected bytes | Git blob SHA-1 |
| --- | ---: | --- |
| VERIZON_2022_10K | 2,315,268 | 92473150ab26a2f8419989bcd2d825c760424f8c |
| COCACOLA_2017_10K | 1,790,599 | 340399e1fd68b05f4efbdba60985302d23c6689e |
| COSTCO_2021_10K | 765,319 | 8969f7a2601c92a9a1a65fcd137b94a868074e29 |
| JOHNSON_JOHNSON_2022_10K | 1,941,368 | eba313ca98f81a2cabc19c7dd931c92c3def3a66 |
| 3M_2022_10K | 1,655,681 | ac32e3076d5fc0378b5123b204eece5fc5d39dac |
| AMERICANWATERWORKS_2021_10K | 1,975,636 | b716b0e0aece594ccb45d0006b183e49e24a1595 |

Total expected body size is 10,443,871 bytes. These inventory entries described
ordinary file-mode blobs before acquisition. The acquisition gate checks
PDF magic, exact byte length, and the Git blob digest over the header plus bytes,
then record an independent SHA-256. Git's [object-format explanation](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
describes the blob header and digest; a plain file SHA-1 is not the Git object ID.
Do not infer issuer-byte equivalence, publication timing or extraction quality
from the repository metadata. Reject a pointer/error body rather than resolving
it through an unplanned download path.

## Boundaries and remaining work

The selection preserves seed-17 development membership and excludes mapped
exposed companies. Four opaque TAT-QA exposure groups lack issuer identities;
there is no global cross-suite issuer-disjointness claim. The conflicting
FOOTLOCKER_2023_annualreport metadata is recorded and lies outside this exact-10K
selection. No final-partition group was recruited and no download-based replacement
is allowed. Selection parses full JSON rows but projects only metadata; question,
answer and evidence fields were not inspected or used.

The [frozen acquisition](acquisition-report.md) verifies all six repository bodies
(10,443,871 bytes) with no failures or retries. The subsequent
[preparation/extraction](preparation-report.md) is complete under a frozen rubric
and development reservations: 981 pages, 34,904 emitted lines, five empty-native-text
pages and zero warnings. [Outcome-blind annotation](annotation-report.md) and
independent page review are complete: six mapped location packets across ten
referenced pages, with no adjacent-page expansion. Semantic caveats remain explicit
for 3M, Coca-Cola and Verizon. Comparison remains unexecuted and must keep policies/budget fixed; it cannot
retune from these cases. This preparation is not a benchmark score.

All 329 tests and lint pass. Six bodies have been byte-verified and natively
extracted; selected task/reference records were prepared by code. All six packets
were independently reviewed and frozen before retrieval; this is not human finance
validation. No retrieval/context run, paid call or holdout run has occurred. Spending
remains $0.4814193.

Independent metadata-only review verified the 394-path non-truncated tree, all six
ordered blob entries, exact sizes, source links and response/selection hashes.
That review performed no network requests or financial-content inspection.

## Comparison implementation

The [runner](compare.py) and [plan](comparison-plan.md) are independently reviewed.
The reviewed driver SHA-256 is
`7a6a0e1f62586418cd5bd0eab20fe167b74f4fef5071d1846b7e74f56db70d53`.
Nine synthetic tests cover label-free collection, byte-exact replay before packet
parsing, identical histories, empty searches, failed read slots, durable search/read
interruption, blocked contexts, post-replay tampering and policy divergence. All
329 repository tests and lint pass. No real cohort search has run; freeze the exact
protocol before execution. Historical policy code and production defaults are
unchanged.
