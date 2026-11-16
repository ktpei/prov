# Financial conventions and evidence boundaries — 2026-11-16

Generic primary-source research by an independent fresh-context coding agent.
No issuer report or benchmark question was queried. This proposes future protocol
design; it does not revise frozen judgments, historical scores or reserved items.

## Evidence and scope

The [CFA Institute Financial Ratio List](https://www.cfainstitute.org/sites/default/files/-/media/documents/support/programs/cfa/cfa_program_level_ii_financial_ratio_list.pdf)
acknowledges alternative practical definitions and declares examination defaults
when questions omit a formula. Its debt measures use interest-bearing debt and
exclude accounts payable and accrued expenses. The inspected PDF has no visible
edition date; a future protocol should preserve the exact version and hash.

The SEC's [Beginners' Guide to Financial Statements](https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide)
instead illustrates debt-to-equity with total liabilities and explains that useful
ratio levels vary by industry. The page is dated February 5, 2007 and explicitly
is educational material, not a legal interpretation or SEC policy. These sources
demonstrate competing definitions; neither supplies a universal benchmark formula.

Canada's Translation Bureau [currency-symbol guidance](https://our-languages.canada.ca/en/writing-tips-plus/canadian-dollar-symbol)
distinguishes several national dollar currencies and country-qualified notation.
A bare dollar symbol does not uniquely identify a national currency. This is
linguistic guidance, not an accounting standard.

SEC [Financial Reporting Manual Topic 6](https://www.sec.gov/about/divisions-offices/division-corporation-finance/financial-reporting-manual/frm-topic-6),
sections 6600–6640, distinguishes reporting currency, functional measurement and
currency disclosures, including scoped exceptions for domestic registrants.
Relevant sections have update dates spanning 2008–2020. SEC filing status alone
does not establish an unconditional USD rule. Staff guidance has a particular
regulatory scope; do not apply IFRS or US GAAP requirements indiscriminately.

The official [Form 10-K](https://www.sec.gov/files/form10-k.pdf), inspected version
marked 02-25, asks for the fiscal-year endpoint. SEC
[FRM Topic 1](https://www.sec.gov/about/divisions-offices/division-corporation-finance/financial-reporting-manual/frm-topic-1)
section 1365.7 recognizes 52–53-week fiscal years. Section 1450.1's calendar-year
presumption applies when no closing date has been adopted. Missing a date in a
retrieved excerpt does not establish that condition. Relevant passages have
2009–2010 update dates; this research is not a current legal-compliance opinion.

NIST's [AI RMF Playbook Measure](https://airc.nist.gov/airmf-resources/playbook/measure/),
especially 1.1 and 2.5, connects evaluation measures with intended use, operating
conditions, assumptions, validity and limitations. The live page says AI RMF 1.0
is being updated. A textual-support diagnostic therefore needs its own purpose
statement rather than standing in for overall analyst competence.

[AmbigQA](https://aclanthology.org/2020.emnlp-main.466/) (Min et al., EMNLP 2020)
models ambiguity through plausible answers paired with disambiguated questions.
It provides a precedent for interpretation-aware answer sets. Its open-domain QA
findings and ambiguity frequency cannot be transferred directly to finance.

## Prospective protocol proposal

Declare the permitted evidence boundary before validation: cited spans, pages,
document-wide headings/notes, supplied source metadata and any external references.
Distinguish ordinary arithmetic from an undeclared substantive assumption.

Publish a versioned convention register with scope, reporting framework where
relevant, formula, precedence, source/version and exceptions. Explicit question
instructions override defaults; issuer-defined measures require their definitions.
Do not use a source's existence elsewhere to claim it was delivered to the model.

| Dimension | Declare before evaluating |
|---|---|
| Currency | Symbol transcription versus named reporting currency; permitted currency disclosure/inheritance and conversion evidence. A dimensionless ratio need not assert an irrelevant USD identity. |
| Period | Fiscal-year label versus exact endpoint; instant versus duration facts; transition and 52–53-week periods. |
| Ratio | Numerator components, consolidation/attribution scope, denominator and averaging, debt/lease treatment where relevant, sign, display scale and rounding. |
| Classification | Supplied threshold versus analytical heuristic, boundary equality, comparison population, and treatment of unspecified thresholds. |
| Ambiguity | Interpretation-specific formulas, required evidence and accepted answers; qualified answers and clarification requests where warranted. |

Record evidence support, convention applicability and question determinacy
separately. A bounded-evidence task can require claims to follow from its stated
boundary without undeclared substantive conventions. An analyst task can permit
published defaults, wider document context and justified qualifications. Neither
automatic abstention nor choosing any plausible interpretation deserves blanket
credit. New valid interpretations discovered after freezing become adjudication
issues and separately versioned revisions, not silent score improvements.

## Ingestion implications and limits

Preserve the provenance of currency, scale, fiscal endpoint, entity scope and
table-header associations as distinct facts. Inherited context should identify
its source span and scope rather than being inserted as an uncited normalized
fact. Native text alone may lose table geometry; extraction identity checks do
not establish correct header/value association. A future structured sidecar can
expose explicit versus inferred fields and unresolved conflicts, but it needs a
prospective acceptance test before adoption. No such feature is implemented here.

Research disclosure: generic searches incidentally returned unnamed 2026 EDGAR
snippets for CIKs 1835632 and 895447. Neither was opened or used; no reserved issuer
or report was queried. The lead consulted the metadata-only exposure audit.
These recommendations improve reproducibility, not perfection, and six post-hoc
coding-agent cases cannot establish broad financial reliability.
