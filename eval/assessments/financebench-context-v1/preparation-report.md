# Six-task preparation and native extraction completed

All six frozen tasks were prepared and all six local originals extracted. The
corpus contains **981 physical pages and 34,904 emitted lines**, with zero parser
warnings and five pages lacking native text. This is an ingestion result, not
verified financial completeness or a retrieval/context score.

The [plan](preparation-plan.md) was committed with implementation `18125ca` and
six development reservations before content processing. The exact input/runtime/
package protocol was frozen in `2f5199b`. [Result](preparation-result.json) and
[summary](extraction-summary.json) bind prepared files, per-source manifests,
original/text identities and the aggregate corpus. Local artifacts are under
`runs/financebench-context-v1-preparation/{prepared,corpus}`.

| Document | Pages | Emitted lines | Pages without native text | Warnings |
| --- | ---: | ---: | --- | ---: |
| Verizon 2022 | 124 | 5,171 | None recorded | 0 |
| Coca-Cola 2017 | 197 | 7,092 | None recorded | 0 |
| Costco 2021 | 76 | 2,500 | 1 | 0 |
| Johnson & Johnson 2022 | 151 | 5,627 | None recorded | 0 |
| 3M 2022 | 252 | 8,854 | None recorded | 0 |
| American Water Works 2021 | 181 | 5,660 | 151, 153, 155, 157 | 0 |

Extraction used pypdf 6.21.4 in the existing layout mode, PDF diagnostics v2,
without fonttools, OCR, repair, alternate downloads or parser changes. Empty pages
retain explicit placeholders and original page locations. They may be genuinely
blank or may require another extraction method; no visual determination has been
made. Zero warnings does not establish correct table columns or complete text.
The legacy ingestion `complete` flag is not a quality endorsement; all six sources
explicitly retain `text_completeness: not_verified`.

Preparation filtered to the six selected IDs before adaptation and applied the
frozen reference registry (no previously registered issue IDs matched). The selected
order remains separate from the task-hash preparation order. Original seed-17
membership was checked independently of the development reservations. Prepared
questions/references were serialized by code but have not yet undergone annotation
review. No selected question text, answer or evidence was used to tune the pipeline.

All six original hashes match acquisition receipts, and prepared file hashes,
per-source manifests, originals/text and aggregate binding were checked before
completion. Source input specs contain only whole-document metadata and original
paths; benchmark question/reference content does not enter extraction.

## Remaining gate

Author and independently review complete evidence packets under the frozen rubric,
using reference-aware but retrieval-outcome-blind page review. Record all material
period/unit/entity/operand/qualification roles and any unresolved references. Keep
all six selected slots. Do not run search, reads or retention comparisons until
packet bytes and a separate comparison protocol are frozen. Visual/native-text
quality must be assessed on the allowed pages; extraction success alone is not
sufficient. Any scope expansion must be recorded before coverage is observed.

All 320 tests and lint pass. Five new synthetic tests cover six-slot success,
partial extraction failure, interruption, changed inputs, prepared-write durability
and later manifest mutation. Independent implementation review verified the fixes
before execution. No network or paid model calls occurred; recorded spending
remains $0.4814193. The original holdout and historical results are unchanged.

Independent metadata/hash review verified the full input/output chain and prepared
order without inspecting question/reference/text content. The emitted-line count
comprises 34,899 native lines plus five empty-page markers. No additional extraction
or network calls occurred during that review.
