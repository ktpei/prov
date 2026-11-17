# Saved-response size diagnosis — 2026-11-16

Full-document extraction diagnostics, repeated in every read, dominate the context
cost. Arithmetic on the frozen thirty read responses finds 1,045,305 serialized
output-string characters in total; extraction metadata contributes 831,345
(79.53%), including 813,590 for the per-page diagnostics arrays. Literal evidence
text contributes 127,232 (12.17%); each read contains only 1,438–8,707 text
characters, below the 18,000-character text cap.

| Source | Full-page diagnostics characters/read | Required footprint at 1 / 3 / 5 reads |
| --- | ---: | --- |
| Costco | 12,522 | 24,560 / 25,299 / 26,213 |
| American Water Works | 30,014 | 45,484 / 39,819 / 47,303 |
| Verizon | 20,536 | 31,620 / 33,476 / 35,926 |
| Coca-Cola | 32,710 | 44,973 / 43,660 / 44,003 |
| 3M | 41,907 | 56,298 / 56,843 / 57,086 |
| Johnson & Johnson | 25,029 | 35,936 / 39,212 / 38,821 |

Required footprint includes latest search, latest read, and omission notices for
earlier reads. These minima reproduce all 4/5/5 blocked projections before either
policy considers optional ordering. No new retrieval, read, projector or policy
experiment was executed for this diagnosis.

The [machine-readable decomposition](response-size-diagnosis.json) binds saved
run and code hashes and contains per-read additive accounting. The remaining
additive components are 63,573 characters for line structure/page locations,
22,315 for other response fields/container, and 840 for source-text escaping.
Source whitespace (58,021) is already included in literal text. JSON formatting
whitespace and outer-serialization overhead are overlapping diagnostic views,
not additional terms in that sum.

The smallest supported hypothesis is that document-wide diagnostic delivery is
the main capacity constraint here. A subsequent opt-in response projection can
retain diagnostics for the actual returned physical pages while preserving global
warnings, uncertainty flags, full-document counts and a hash of the full original
diagnostics. The complete original metadata must remain in the corpus. Such a
projection does not itself fix retrieval, validate financial answers or guarantee
that every response fits the context limit. It requires a separately bound
implementation and experiment; this diagnosis does not measure its benefit.
