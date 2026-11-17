# Financial source ingestion research

**Recommendation.** Start with source-aware search and table-aware reads for native HTML. Keep native PDF extraction as the baseline and compare layout parsing and selective OCR on pinned documents. Use SEC filings and XBRL for tagged facts, with the source document location available for inspection.

## Reproduced Cloudflare results

The frozen packet contains an earnings release, a 10-Q, an earnings call transcript, and an investor presentation. The loader checks both the original and extracted-text SHA256 hashes. On the six existing development probes, native extraction contains the expected lexical anchors for **5/5** positive-evidence tasks and fixed-query BM25 retrieves all expected anchors for **4/5**. The sixth task tests abstention and has no positive evidence requirement. Anchor matching tests text availability and retrieval coverage. It cannot establish table geometry, correct financial interpretation, or model accuracy. [Source packet](../source-packet.md) · [Saved retrieval report](reports/frozen-evaluation-2026-11-07/fresh-retrieval.json)

```sh
uv run --locked --offline python -m provenance.evaluation \
  --corpus data/cloudflare-2024-q3 \
  --benchmark eval/company_fresh_tasks.json
```

The `fresh-03` question explicitly asks for the cash-flow statement in the **earnings release**. With the packet and frozen query unchanged, all five current search hits come from the 10-Q. An in-memory diagnostic restricting the same search to the release returns the table title and headers in `L162–L193` and a matching purchases row in `L186–L217`. No retrieved window contains all five expected anchors together. The frozen evaluator checks the union of windows per source, so it can count anchors spread across windows without verifying their association. [Task and expected evidence](company_fresh_tasks.json) · [Current retrieval evaluator](../provenance/evaluation.py)

In the original release, the title and unit (`L172`), nine-month and year headers (`L174–L175`), and investing activity row (`L201–L203`) belong to the same HTML table. The source uses ordinary `td` cells for merged headers. The closing parenthesis occupies a separate cell from the amount. A later reconciliation table repeats the nine-month value and also lists quarterly values. The expected result is **USD 111.884 million** as a positive cash-outflow magnitude, backed by the correctly signed cash-flow statement row and the matching year and unit headers. [Original earnings release](https://www.cloudflare.net/news/news-details/2024/Cloudflare-Announces-Third-Quarter-2024-Financial-Results/default.aspx) · [Frozen native extract](../data/cloudflare-2024-q3/cloudflare-q3-2024-release.txt)

The following tags and contexts were checked in the pinned 10-Q for accession `0001477333-24-000085`. All three are undimensioned USD facts with scale `3` and decimals `-3`.

| Concept and fact ID | Context | Displayed value before scaling |
| --- | --- | ---: |
| `us-gaap:AssetsCurrent`, `f-43` | `c-4`, instant on 2024-09-30 | 2,163,878 |
| `us-gaap:LiabilitiesCurrent`, `f-71` | `c-4`, instant on 2024-09-30 | 641,615 |
| `us-gaap:PaymentsToAcquirePropertyPlantAndEquipment`, `f-457` | `c-1`, duration 2024-01-01 through 2024-09-30 | 111,884 |

The payment tag carries a positive magnitude. Preserve that source representation separately from the signed entry in the earnings release. The filing is corroborating evidence for the metric and a fixture for the XBRL adapter. An answer explicitly scoped to the release must still open and cite the release. [Original Cloudflare 10-Q](https://www.sec.gov/Archives/edgar/data/1477333/000147733324000085/cloud-20240930.htm)

## First implementation slice

1. Add explicit source scoping to a new retrieval version. When a question names the earnings release and the source resolves uniquely, search that source. For an issuer-wide question, search all eligible sources. Apply an explicit historical cutoff to availability time, separately from the fact's reporting period.
2. Add a table sidecar to the original HTML. Assign table, row, and cell IDs. Track row and column spans, raw cell text, logical headers, table title, units, and applicable footnotes. Start with the cash-flow table and retain the original locator for every component. Use title and header text to help rank the row.
3. Return the selected row with linked header and unit spans in one bounded read. Render citations from the verbatim evidence spans. When returning a typed numeric cell, include the exact decimal and raw sign, currency and scale, instant or duration, and the original spans establishing those fields. Mark unresolved associations explicitly.
4. Keep frozen originals, legacy text, line locators, and retrieval versions available for saved runs. Record independent hashes and parser/configuration versions for the sidecar and challenger outputs. Preserve the existing scorer and introduce a new full-evidence scorer. Replay all six saved grades against the frozen baseline before promoting the new path.

## Comparison protocol

Freeze the original hashes, permitted source set, queries, budgets, and evidence labels. Annotate the original HTML table or PDF page region with the value, label, period, unit, sign, and material footnotes. Keep annotations and answer keys outside retrieval. Start with the Cloudflare regressions and add independently reviewed documents from other issuers and document types for promotion decisions.

| Condition | Fixed inputs | What to measure |
| --- | --- | --- |
| Native HTML and native PDF | Frozen originals, current stdlib HTML and pypdf layout implementations | Text available, correct cell associations, stable original locations, baseline wall time |
| Native HTML plus table sidecar | Same originals, extracted text, and query set | Complete evidence in a bounded read, wrong-table hits, row and column association errors |
| SEC Company Facts and filing-level Inline XBRL | Issuer, metric, filing eligibility, and expected context | Exact concept, accession, original locator, period, unit, scale, and dimensions. Record aggregate coverage gaps separately from incorrect matches. |
| Docling layout and table structure with OCR disabled | Same PDFs, labels, host, and retrieval settings | Value-to-header association, reading order, page and region provenance, runtime, and peak memory |
| Same Docling configuration with selective OCR | Same documents and region labels | Incremental recovery on image-only or unreadable regions, duplicate text, and regressions on native text. Include a mixed page with a readable title and an image-only table. |
| Full-evidence retrieval ablation | Same extraction snapshot, permitted sources, queries, top-k, and total read payload budget | Compare legacy BM25, explicit scoping, header-linked reads, and both changes together. Distinguish ranking misses from context omitted on read. |

Compare native PDF text with layout analysis before enabling OCR on scans or mixed image regions. Pin parser and OCR engine versions, settings, and any rendering resolution. Check chart series, axis, and legend relationships separately from text recognition. The SEC aggregate APIs cover non-custom taxonomy facts applying to the entire filing entity. Use filing-level Inline XBRL where custom tags or dimensions are needed. Resolve accession and availability rather than relying on a Frames result for point-in-time answers. [pypdf text extraction documentation](https://pypdf.readthedocs.io/en/latest/user/extract-text.html) · [Docling pipeline options](https://docling-project.github.io/docling/reference/pipeline_options/) · [Docling page and region provenance](https://docling-project.github.io/docling/reference/docling_document/) · [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) · [SEC Inline XBRL](https://www.sec.gov/data-research/structured-data/inline-xbrl)

## Acceptance fixtures

- **Cash-flow source, sign, and scale.** `fresh-03` returns the statement row, investing activity label, nine-month 2024 column, and thousands header. Reject the later reconciliation, 2023, quarterly numbers, the neighboring software row, and a detached parenthesis. The statement value is negative and its requested magnitude is positive.
- **Instant versus duration and as-of eligibility.** Keep the balance sheet facts distinct from the nine-month payment fact in the same filing. Exclude that accession before its public availability. Include fixtures for a later filing that repeats a prior period and for an aggregate lookup that lacks a filing-level custom or dimensional fact.
- **GAAP and adjusted measures.** `fresh-01` binds the correct rows to the three-month 2024 column even though nearby columns cover 2023 and nine-month periods. The rendered evidence preserves separators.
- **Native PDF preservation and chart association.** Transcript original page 4 is the prose control. Investor deck original page 105 tests chart-series association. A correct number attached to the wrong series fails. Add independently labeled image-only and mixed-page fixtures for OCR.

For extraction, score the complete typed-cell association per expected cell. For retrieval, report complete evidence recall per answerable task at a fixed budget. Count failures where the correct number appears under the wrong row, period, unit, or source. Include all attempted inputs and record unresolved cases, latency, and payload size. Promote a challenger only after it passes required regressions and improves the target slice on reviewed documents at an acceptable resource cost. Keep these scores separate from later model answer accuracy. [Frozen Cloudflare tasks](company_fresh_tasks.json) · [PDF spot checks](../source-packet.md) · [OmniDocBench annotation and evaluation methodology](https://openaccess.thecvf.com/content/CVPR2025/html/Ouyang_OmniDocBench_Benchmarking_Diverse_PDF_Document_Parsing_with_Comprehensive_Annotations_CVPR_2025_paper.html)

**Experiment status.** The frozen retrieval baseline, release-scoped diagnostic, original HTML table structure, and three filing tags above were verified offline. The table sidecar, SEC adapter comparison, Docling runs, selective OCR comparison, and full-evidence ablation are proposed experiments. These probes used no model calls.

## Native-text visibility gap — 2026-11-16

Independent synthetic review of `DocumentHTML` found that the legacy text path
is not equivalent to native table sidecar v2. It ignores `hidden` and inline
hiding styles: `42<span hidden>999</span>` can become `42999`. A hidden heading
can also alter subsequent section metadata. Counter-based suppression can end on
an unrelated closing tag, and visible block-separated numbers within a cell can
merge. These are source-quality defects even when original/text hashes validate;
a hash establishes identity, not correct extraction.

Preserve existing frozen corpus bytes and legacy replay. Before new HTML corpus
acceptance, implement and explicitly select a versioned text path, or declare
legacy text ineligible and restrict the assessment to independently verified
original-HTML sidecars. Reuse the bounded visibility predicate rather than the
entire table geometry parser; narrative text, block boundaries, optional cell
closures and malformed suppression require their own tests. External CSS and
rendered visibility remain unresolved. No repaired text parser or new-corpus
acceptance is claimed in this finding.

The [new assessment plan](assessments/native-html-v1/plan.md) also separates a
search-only runtime from later annotation grading. Its proposed six filing
identities were selected from metadata; acquisition, question authoring and source
annotation are still pending implementation and provenance gates.

### Opt-in versioned repair

`native-html-text-v2` now provides a separate native-text path through
`extract(..., html_text_version=...)`, `ingest(...)`, and the ingestion CLI's
`--html-text-version`. The default remains `stdlib-html-v1` for exact legacy replay.
V2 shares the bounded inline-hiding predicate but has its own text/suppression
stack. It suppresses templates, preserves visible block/heading boundaries and
cell separators, handles optional cell/row endings within the nearest table, and
rejects ambiguous hidden closures/self-closing elements. Visible inline XBRL,
zero and parentheses remain text. It makes no browser-rendering or completeness
claim; parser identity and unresolved CSS limitations are recorded in metadata.

Independent adversarial review found and fixed two additional issues before
commit: implicit table starts escaping a suppressed template/XBRL wrapper, and
heading line breaks losing currency context. Eight focused tests cover those
cases plus inherited hiding, nested tables, malformed suppression and legacy
replay. Real-source diagnostics are separate from these synthetic checks.
Existing corpus files are never rewritten by selecting this new path.

## Read-response diagnostic scope — 2026-11-16

The [six-source comparison](assessments/financebench-context-v1/comparison-report.md)
found five blocked five-read projections under both retention policies. Arithmetic
on the saved responses attributes 79.53% of read output characters to repeated
extraction metadata; this is not an evidence-text limit failure. The
[opt-in returned-page projection](read-extraction-design.md) preserves all global
warning/uncertainty fields and a hash/reference to full diagnostics, changing only
which full-page records accompany an excerpt. Full metadata stays in the corpus
and remains the default response mode. Independent review and synthetic checks
pass; no compact-mode cohort outcome is measured yet. Historical protocols and
reference answers remain unchanged.

## Retrieval interpretation and primary research — 2026-11-16

The [new review](retrieval-research-2026-11-16.md) distinguishes missing frozen
locations from missing semantic support; 3M has relevant segment tables outside
its original packet. Five primary papers motivate a proposed matched page-context
ranking ablation, with no new results yet. Incidental Verizon 2021 and Amcor 2020
examples are registered as development exposures. The compact read mode is now
available through the CLI, recorded/replayed by both engines and bound to resume
identity; full metadata remains the default.
