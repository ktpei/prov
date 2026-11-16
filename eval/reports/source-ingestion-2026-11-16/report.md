# Source-ingestion diagnostics — 2026-11-16

Three FinanceBench originals were acquired from the pinned repository mirror:
Nike 2023 (106 pages), Ulta Q4 2023 earnings (9), and Walmart 2018 (304).
All 419 pages have locations; Walmart page 60 has no native text. That absence
needs visual classification before choosing OCR. Corpus selection is restricted
to selected task documents, not open-web or entire-FinanceBench retrieval.

A bounded exploratory font probe compared pypdf 6.21.4 without fontTools against
the same extractor with fontTools 4.68.0 on Nike pages 1, 37, 38, 105, and 106.
These pages were selected because a direct font-resource scan found CFF Type1
fonts without ToUnicode, not because benchmark answers failed. Each page had a
30-second timeout. Peak process memory was recorded, without a hard memory cap.

All five extracted-text hashes were identical. Warning counts fell from 87 to
zero; text recovery did not improve. Missing warnings therefore do not establish
correct extraction. No dependency promotion follows from this experiment.
[Exact versions, hashes, counts, timing, and limitations](font-probe.json).

The new ingestion diagnostics retain bounded warning samples and counts by page,
plus parser/fontTools versions. They preserve extracted text and mark completeness
unverified. Frozen corpus files remain unchanged. Earlier extraction artifacts
lack these diagnostics and must not be represented as warning-free.

The pinned pypdf implementation explains the optional CFF font fallback; table
layout still requires separate evaluation. [pypdf source](https://raw.githubusercontent.com/py-pdf/pypdf/6.21.4/pypdf/_cmap.py),
[extraction limitations](https://pypdf.readthedocs.io/en/6.21.4/user/extract-text.html).

Next acceptance is a small independently labeled slice: original visual regions,
exact numeric cells, signs, hierarchical headers, units, periods, and footnotes.
Measure extraction concordance, table geometry, header association, and retrieval
separately. Page recall and structural similarity do not prove financial support.
The HTML sidecar currently retains geometry but does not resolve semantic headers.
[W3C header relationships](https://www.w3.org/WAI/tutorials/tables/multi-level/),
[GriTS topology/content/location distinction](https://arxiv.org/abs/2203.12555).

A source-retrieval diagnostic is being implemented with fixed question-only queries,
top-five retrieval, original-page evidence concordance, and exact corpus bindings.
Gold stays on the evaluation side. Full-agent paid execution remains disabled.
