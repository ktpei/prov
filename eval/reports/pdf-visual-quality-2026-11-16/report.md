# PDF visual source review — 2026-11-16

Two independent coding agents and the lead reviewed four evidence pages for the
three already-exposed FinanceBench development tasks, plus one empty-page
diagnostic. This is not human financial validation or whole-document completeness.
No model calls, OCR, new retrieval experiment or score changes occurred. Exact
source/render hashes and review scope are in the [receipt](review-receipt.json).

## Walmart: retrieval failure, not missing operands

For `financebench_id_06247`, physical page 57 (printed 55) shows FY2018 cost of
sales 373,396, with fiscal years ended January 31 and millions except per-share
units. Native L2173–2174 and L2180 preserve the headings and operand. Physical
page 59 (printed 57) shows January 31 balance-sheet inventories 43,783/43,046 and
accounts payable 46,092/41,433 for 2018/2017, all in millions. Native L2226–2227,
L2232 and L2249 preserve those associations. The specified average-payables over
purchases calculation gives `365 × 43,762.5 / (373,396 + 737) = 42.694209…`, matching
the reference's 42.69. Accompanying-notes pointers remain; those notes were not reviewed.

The failed page-57 exact-concordance comparison reflects two em dashes omitted
from benchmark evidence on the debt-extinguishment row. They are visible in the
original and correctly retained at native L2188. Page 59 matches normalized
benchmark evidence. The unchanged selected-corpus and document-scoped top-five
runs miss both required pages. OCR is not indicated for these inspected operands;
the remaining failure is retrieval coverage.

Physical page 60 renders with no readable content apart from a horizontal rule.
Its zero-native-text status does not demonstrate an extraction failure. Do not
interpret every empty page as requiring OCR, or silently replace it with invented
text. This classification applies to this rendered page only.

## Nike: signs and period preserved

For `financebench_id_01163`, physical page 62 (printed 58) shows the year ended
May 31, 2023 and dollars in millions. Operating cash flow is 5,841, investing 564,
and financing (7,447). Headers at native L2558–2561 and totals at L2577/L2584/L2592
preserve scale, period and outflow parentheses. The accompanying-notes pointer is
at L2603. No relevant omission was found in this inspected page; operations is
highest among the three signed cash-flow totals.

## Ulta period convention

For `financebench_id_00601`, physical page 2 explicitly labels its annual section
“For the Full Year of Fiscal 2022.” Annual SG&A increases from $2.1 billion to
$2.4 billion while the sales ratio falls from 23.9% to 23.5%. Lower marketing
expenses and incentive-compensation leverage are partly offset by corporate
overhead and store payroll/benefits deleverage. Native L63 and L75–80 preserve
the annual heading, amounts and qualifications. The separate quarterly paragraph
at L46–52 uses 23.8% to 23.6%; it must not substitute for annual evidence.

The question says FY2023, but the upstream reference explicitly assumes a
year-ending convention for the period the company calls fiscal 2022. This is a
period-convention ambiguity, not a newly discovered wrong numeric answer. Page 2
does not independently establish the reference's January 28, 2023 end date.
Content-bound issue `reference-d00daa9a06589412` now records the need for review.
The original question, reference answer and both model-input conditions remain
unchanged. Existing frozen preparations and score records are not rewritten;
new preparations can apply the updated nine-issue registry.

## Page diagnostics and reproduction

`pdf-extraction-diagnostics-v2` records every physical page's native nonempty-line
count, non-whitespace character count, emitted line bounds and warning count,
plus a structured empty-native-text page list. Counts are computed before an
empty-page placeholder is emitted. They support review selection, not visual
completeness or automatic OCR decisions. Extraction remains native-only.

[Replay diagnostics](page-diagnostics.json) cover all 419 pages: Nike 106, Ulta 9,
Walmart 304. Extracted text bytes and per-line page locations match the frozen v2
corpus exactly. Only Walmart page 60 has no native text. Metadata changes apply
to future ingestion; the frozen corpus manifest is unchanged.

Render with `pdftoppm -f PAGE -l PAGE -r DPI -singlefile -png ORIGINAL PREFIX`.
Poppler 26.02.0 was used at 150 DPI for the four evidence pages and 120 DPI for
Walmart page 60. PNGs remain local; their hashes and paths are retained in the
receipt. Lint and all 265 tests pass, including empty/whitespace/None page handling,
placeholder exclusion, signs/zero preservation and exact line mappings.

Next work should improve question-only retrieval of the missing Walmart operand
pages under a separately recorded development experiment. Visual checks on these
few exposed pages do not authorize broad extraction or semantic accuracy claims.
