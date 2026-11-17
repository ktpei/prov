# Masked evidence preparation — 2026-11-16

All six masked packets are prepared and independently integrity-audited before
financial evidence judging. The [builder](prepare_evidence.py) and
[review instructions](evidence-review-instructions.md) were committed at `dcb5aa7`
after review and seven synthetic tests. All 385 repository tests and lint pass.
The frozen stage-1 interpretations and original benchmark results remain unchanged.

| Packet | Locked interpretations | Deduplicated excerpts | Full review-only pages |
| --- | ---: | ---: | ---: |
| Q01 | 1 | 14 | 6 |
| Q02 | 2 | 12 | 6 |
| Q03 | 1 | 10 | 5 |
| Q04 | 5 | 10 | 6 |
| Q05 | 5 | 11 | 7 |
| Q06 | 2 | 11 | 6 |
| Total | 16 | 68 | 36 |

The page supplement contains 1,469 source lines. Both judges will receive identical
case packets. Only actual returned lines from the two fixed methods' first five
saved reads are pooled, plus original frozen annotation spans. Exact duplicate
spans merge; all origins remain in custodian-only metadata. Requested-but-unreturned
lines never enter excerpts. Every distinct touched physical page appears once as
review-only context; there is no adjacent-page expansion, new retrieval or unused
candidate-pool supplement.

Reviewer packets preserve literal questions, locked requirements, source identities,
line numbers and exact native text. They omit retrieval ranks, method names, control
status, old rubric roles, reference answers and outcomes. Deterministic hashed
ordering assigns opaque excerpt IDs. Full pages do not automatically count as
retrieved or retained evidence; any later scoring must match actual saved delivery.

The [receipt](stage-2/receipt.json) binds 11 inputs and seven output files (six
reviewer packets plus the separate custody map). An independent
[audit](evidence-packet-audit.json) verified all hashes, exact inventory, source
slices, interpretation dependencies and in-memory reconstruction. It did not judge
financial sufficiency or extraction geometry. Tests cover truncation, duplicates,
failures, masking, page mappings, source/range changes, changed frozen plans and
late output corruption.

Blinding is limited: short control-like spans or excerpt granularity may suggest
provenance, and public source/question identities may be recognized. This is
workflow isolation, not an access-control guarantee. Financial evidence review
has not started. Judges must assess every locked interpretation separately and
record proposed rubric changes explicitly. No new accepted alternatives or scores
exist, and reserved validation content remains closed.
