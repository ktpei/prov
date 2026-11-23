# Captured evidence review

November 23, 2026. Reviewer: independent coding agent using saved inputs, read
receipts and captured source text. No additional retrieval, reserved-content access,
or reference changes. This is diagnostic inspection, not human finance validation.

## Quick development cases

The first treatment's nine exact matches had no clear metric, period or unit error
in inspected evidence. Ameresco and freee used supported rounded source values.
Mitsui remained a source/reference discrepancy. iRhythm's rounded 13.7 million is
explicitly reported and supported; the more precise statement value 13.677 million
is also available. Neither should be selected simply to improve exact scoring.

For the second treatment:

| Case | Finding |
|---|---|
| SBI | Nine-month cumulative EPS substituted for the requested quarter, despite acknowledgment in the answer. Confirmed semantic error with valid quotes. |
| PayPay | Fiscal Q3 selected where the reference aligns with fiscal Q2/calendar Q3. Period convention error, not arithmetic. |
| Mitsui | Captured official FY-ended-March-2023 Energy row supports 58.7; reference is 92.7. Reference/period discrepancy remains unresolved. |
| Lions Gate | Captured standalone-quarter December-2022 row supports 38.6; reference 76.7 appears in a comparative nine-month December-2021 column. Preserve mismatch pending proper reference review. |
| Kewpie | Exact −4.0 billion amount is supported; explanatory “January–December 2023” assertion is not supported by the captured deck. |
| Nitto Boseki | Exact 6,965 million supported for April 2021–March 2022. |
| Ameresco, Aditya Birla, YDUQS | Tolerance-only differences reflect explicitly reported rounded source values. |

These findings show three distinct checks: numerical matching, whether the cited
amount is in the source, and whether the entire answer addresses the requested
financial meaning. The benchmark's quote replay covers only the second check's
textual component. No fully supported accuracy is inferred from it.

## Frozen full-policy diagnostic sample

Selection: first six completed numerical answers outside quick25, in fixed full
manifest order. This selects answer-producing cases and is not representative of
all questions. The reviewer judged safe input and captured read evidence before
consulting these six references. The full policy had already been frozen; findings
were used only for reporting, not to change the running treatment.

| Task | Evidence-first assessment | Reference comparison |
|---|---|---|
| daloopa-aaf4cb649b25dc9c — HUTCHMED | FY2022 R&D expense magnitude and units supported; positive magnitude explained despite accounting parentheses. | Agrees. |
| daloopa-79ec59a0da61241a — Sichuan Kelun | Q1 2022 consolidated R&D amount and yuan unit supported. Source is a third-party filing transcription; original-document authenticity not independently checked. | Numerically agrees, provenance caveat remains. |
| daloopa-4a5df7b8a6524628 — Samsung | 3Q23 combined SG&A/R&D row and units support the amount. Flattened extraction still allows a coherent mapping. | Agrees. |
| daloopa-2df75ba0dc6be180 — MMG | Sentence identifies Kinsevere copper cathode, 2019, and tonnes. | Agrees. |
| daloopa-883efd75dc427d4d — Fudan | Design segment external revenue, FY2023 and currency available in read evidence. | Agrees. |
| daloopa-9a6552d7f883dd7a — JAPEX | 2,885 million yen supports year ended March 2023; “FY2023” convention ambiguous before reference inspection. | Reference expects 3,536 for year ended March 2024 in the same table: fiscal-year alignment mismatch. |

Improved navigation does not by itself solve fiscal-year naming, cumulative versus
standalone periods, or original-source authenticity. Those remain substantive
requirements for financial reliability even when the numerical benchmark improves.
