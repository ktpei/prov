# Source-ingestion diagnostics — 2026-11-16

Three FinanceBench originals were acquired from the pinned repository mirror:
Nike 2023 (106 pages), Ulta Q4 2023 earnings (9), and Walmart 2018 (304).
All 419 pages have locations; Walmart page 60 has no native text. That absence
was subsequently rendered and found to contain no readable content apart from a
horizontal rule; it does not establish an OCR requirement. See the
[visual review](../pdf-visual-quality-2026-11-16/report.md). Corpus selection is restricted
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

The offline source diagnostic now uses fixed question-only queries, top-five
retrieval, original-page evidence concordance, and exact corpus bindings. Binding
v2 hashes the complete source manifest as well as originals/text, so page mappings
cannot change silently. The newly assembled v2 corpus has identical original and
text hashes to v1 and records Nike's 87 warnings; other PDFs recorded none.

[Baseline result](retrieval-baseline.json): top-one pooled annotated-page recall
1/4; top-three and top-five 2/4. Complete annotated-page coverage is 1/3 tasks at
one hit and 2/3 at three/five hits. Walmart's required pages 57 and 59 were both
missed in the top five. Nike page 62 and Ulta page 2 were reached. This is a
three-task development diagnostic, not general retrieval accuracy or evidence
sufficiency, and measures passage pages rather than snippet contents.

Exact whitespace-normalized evidence concordance is 2/4 excerpts. Examination
shows the two nonmatches contain dashes retained by extraction but absent from
the benchmark excerpt: Walmart adds two dash placeholders; Nike retains dash
punctuation/placeholders and additional page content. These exact-match failures
therefore do not by themselves establish missing financial information. The
metric remains unchanged; visual financial-cell review is still needed.

Gold stays on the evaluation side. Full-agent paid execution remains disabled.

## Declared-document scope ablation

An exploratory follow-up kept the three tasks, original query strings, extraction,
and BM25 ranking fixed, while restricting each query to its already-permitted
`doc_name`. Gold document/page labels were not used for retrieval. This changes
corpus statistics as well as excluding distractor documents, so it is a source-scope
comparison, not an isolated ranking-formula test.

First-hit pooled annotated-page recall improved 1/4 → 2/4. Top-three/top-five stayed
2/4; Walmart still missed both required pages. Nike's required page moved to rank 1.
No new model calls occurred. These inspected development cases do not establish
broader improvement. [Hashes and per-condition results](source-scope-ablation.json).

## Native HTML v2 and packet grading

The independently reviewed hidden-text defect is fixed in sidecar v2. Explicit
hidden attributes and simple inline hiding styles suppress text; hidden cells
retain geometry and an explicit status. Captions and raw scope/headers attributes
are preserved without semantic inference. Block text boundaries cannot merge
adjacent numeric tokens. Valid `rowspan=0` remains explicitly unsupported.

The release retains all 16 tables/253 rows/2,682 cells with unchanged IDs and text;
the filing yields 55/679/8,247. Four frozen evaluator-only packets cover purchases,
R&D GAAP/non-GAAP periods, balance-sheet instants, and per-share scale exceptions.
Structural grader positives and adversarial negatives pass. External CSS, semantic
header association, and agent retrieval of a complete packet remain unverified.
