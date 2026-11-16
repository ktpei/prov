# Validation reservation status — 2026-11-16

Selection was frozen at `768ea06` before metadata-only execution. Independent
review reproduced the exact reservation bytes, hash
`547060f9b42463b7b05ef3c4933a5b39c658996f08f464a068867c00336b33ce`.
All six groups retain original seed-17 development membership. The complete ledger
contains 84 groups/150 tasks, including 16 internal-final groups left untouched.
All 358 tests and lint pass; five selection tests include input-mutation rejection.

| Reserved company | Document | Post-selection issuer audit |
| --- | --- | --- |
| Lockheed Martin | LOCKHEEDMARTIN_2022_10K | No known overlap in checked records |
| American Express | AMERICANEXPRESS_2022_10K | No known overlap in checked records |
| Amazon | AMAZON_2017_10K | Prior issuer exposure in original harness |
| Microsoft | MICROSOFT_2016_10K | Prior issuer exposure in original harness |
| AMD | AMD_2022_10K | No known overlap in checked records |
| Block | BLOCK_2020_10K | No known overlap in checked records |

## Discovered limitation — do not silently repair selection

The selector correctly follows its frozen registry/alias exclusions, but that
registry was not an exhaustive account of known issuer exposure. A root check of
company metadata in `data/corpus/sources.json` found Amazon and Microsoft; the same
manifest also lists Apple, NVIDIA and Meta. The separate Cloudflare corpus lists
Cloudflare. No original task/holdout questions or source text were opened by this
check. [Exposure audit](exposure-audit.json) binds these manifests and records each
slot's disposition. Four TAT-QA issuer identities remain unknown.

Preserve all six slots and the original plan/selector/selection. Do not replace the
two issuer-overlap cases or claim that all six are unseen issuers. The selected
FinanceBench documents and questions remain locally uninspected, so a future
protocol may examine document-level validation while explicitly stratifying the
two known prior-issuer exposures and retaining all six in the overall denominator.
These four-versus-two descriptive strata are fixed now, before outcomes, rather
than choosing a preferred subgroup after observing performance.
Any unseen-issuer claim is limited to four cases with no overlap in checked records,
with unresolved cross-suite exposure still disclosed. This does not establish
model-training non-exposure or population generalization.

## Remaining gates

Validation content is closed. No acquisition, extraction, question/reference
inspection, retrieval, annotation or paid evaluation has occurred. Reserve all six
issuers against further development research and selection. Freeze the final
retrieval policy and prospective validation/annotation protocol before opening
content; record access by role and time. Recheck exposure before opening content.
The page-ranking development comparison on the earlier six exposed cases still
needs its own frozen protocol. Original benchmarks and scores remain unchanged.
