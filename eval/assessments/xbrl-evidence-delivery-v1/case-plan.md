# Proposed development cases

Status: source-reviewed proposal; candidate question execution/scoring has not run.
These cases use an already exposed filing and follow baseline inspection. They
are not held-out, outcome-blind to that baseline, or final machine-grade labels.
Freeze a reviewed role/alternative manifest and budgets before candidate runs.

Keep occurrence delivery, complete role coverage and financial sufficiency as
three separate results. Report table-mapped, narrative/continuation and hidden-tag
controls separately. Exact tagged representation and usable financial evidence
are related but not interchangeable.

| Case | Question | Source requirements and interpretive boundary |
|---|---|---|
| Cash | Provide cash and cash equivalents at June 30, 2025 and December 31, 2024. | Table-8 row6: 24,057 and 108,676, scale3, USD 24,057,000 and 108,676,000. Require metric, both dates, amounts, monetary basis and original occurrence. Normalized next-midnight context boundaries must not change the financial date. |
| Expense | Provide other expense, net, for the three and six months ended June 30, 2025. | Table-10 row23: displayed 1,357 and 2,428; tagged OtherNonoperatingIncomeExpense is -1,357,000 and -2,428,000 USD. Require April1–June30 versus January1–June30 and sign provenance. A positive expense description is not financially wrong solely because the tag is negative. |
| ASR scope | Provide the amount, program scope, initial delivery and settlement details of the ASR agreement entered into May 28, 2024. | Original line2844, F_7a65e687-9aaa-43aa-9c21-a2ca35d20104: 200.0 scale6, USD 200,000,000; instant May28,2024; ShareRepurchaseProgramAxis / AcceleratedShareRepurchaseAgreementMember. Surrounding narrative must distinguish agreement date, initial delivery and November settlement; the context date alone is not a settlement date. |
| Diluted EPS | Provide diluted EPS for the three and six months ended June 30, 2025. | Table-10 row34: 1.27 and 2.46, scale0, USD/shares. Require parent “Earnings per share:” at row32, “Diluted,” correct periods and the exception to the table's thousands convention. The baseline row34 read misses row32. A typed-concept alternative must be separately specified rather than silently equated with visible-label delivery. |
| Declared zero | What does the December 31, 2024 credit-agreement borrowings entry represent? | Table-15 row3, F_cafba24e-d3c2-4afd-aa16-d0e27d4640dc: em dash, declared fixed-zero transform, typed USD zero. Require period and row label. The glyph alone is not an unambiguous typed-zero basis. |
| Nil control | Distinguish the two commitments-and-contingencies nil facts from the zero borrowings fact. | F_d6d79b3b-30b4-41ee-97c3-4c6898ab25cf and F_4887bb55-57d5-47ad-a9e1-931d12ad9e68 are hidden, empty, xsi:nil=true at June30 and December31. Require nil/null, hidden disposition and original-element citations. This representation control does not establish that the company had no commitments. |
| Segment duplicates | Provide operating and reportable segment counts, accounting for repeated disclosures. | Original lines2729/3040: four nested occurrences, two concepts, each “one” to integer1 in unit Segment. Require two concept-specific duplicate pairs with retained citations. Do not sum repeated occurrences or conflate operating and reportable concepts. |
| Continuation | Provide the EPS computation disclosure together with its reconciliation continuation. | F_e962a1dd-89a6-466b-85ba-6a14dd973dd2 at original line2844 explains computation; continuation _1 at line2848 supplies reconciliation. Require both original fragments and their relationship, nested numeric occurrences, period/unit headers. Assembled text is not an original-byte quotation. |

Namespace-resolved concept, dimension and unit identifiers must be used in the
final manifest; short local names here are explanatory. Original line numbers
locate review material, not substitutes for byte/hash-bound citation identity.
Source-derived expectations were proposed by the independent methodology agent;
root directly verified the EPS parent-label gap. Independent source review verified all eight proposed amounts, dates and named
occurrences. The corrections below must enter a frozen role manifest before
candidate question execution/scoring; financial sufficiency remains ungraded.

## Failure controls required of the reader

1. Reject substituted context/unit evidence, including period, dimension or
   USD/share near misses; matching concept or numeric text alone is insufficient.
2. Distinguish actual nil, fixed-zero, empty string, absent evidence and unknown ID.
3. Preserve selected occurrence multiplicity and duplicate membership; synthetic
   inconsistent groups must remain quarantined.
4. Oversized fields need explicit deferred status, length/hash and bounded range
   retrieval. Chunk reconstruction must match the declaration; metadata-only
   output does not receive full-value credit.
5. Reject mismatched source/export identities. Canonical SEC identity cannot
   grant earlier access to the acquired issuer bytes.

The source has 33 instant and 38 duration contexts, 60 with reported dimensions,
plus five unit identities. Its 80 duplicate groups contain 167 occurrences. The
largest assembled text has 109,105 characters, so an atomic 12,000-character
response policy cannot simply return every complete fact object unchanged.

## Independent source-review corrections

- Cash: June occurrence `F_e5f67804-d61f-4693-b6b5-bc0dc62a76e8`; December
  `F_4c8794cc-8811-4e52-890b-d860f1cea2c2`. Visible `$` alone is not a literal
  ISO USD declaration; keep visible monetary basis and explicit unit identity separate.
- Expense: quarter `F_a0b45199-73b0-42c2-a6fe-77fdc1e60302`; six months
  `F_edd6c16b-ae4a-4a83-a7f9-2af3046545ba`. A displayed positive-expense alternative
  cannot receive separate tag-sign-provenance credit.
- ASR question now explicitly requests initial delivery and settlement details.
  The narrative specifies $160 million initially and $40 million remaining balance
  settled in November 2024. `F_6f810be0-3f9c-4a1f-942a-addbb0267f97` is an approved
  amount-occurrence alternative only when accompanied by the required narrative.
- EPS: quarter `F_5fce1a54-f414-4fc1-8128-170f804d790d`; six months
  `F_bdc08fb4-4be8-4bf9-9858-422afb28456a`. Typed-concept and visible-parent-label
  routes need distinct role maps, not automatic equivalent delivery credit.
- Zero: June occurrence `F_5a31b40e-51c3-4469-927d-b890bfdb65fd` is a wrong-period
  control, not an alternative to the December zero. Explicit transform evidence
  is a representation requirement beyond displaying the financial row.
- Nil control requires three occurrences: both hidden nils and the declared-zero
  fact. A visible blank is not an alternative for nil attributes.
- Operating segment pair: `F_72cf521e-5f66-4ad0-86ba-60110438c251` and
  `F_99c15f29-8112-43fa-9d88-af4ec88296a0`. Reportable pair:
  `F_7d1b4054-15e7-4f4b-8a23-67aa2d9095ab` and
  `F_0950315d-b15f-4f60-949b-638175e1317a`. A single occurrence per concept may
  support counts but does not deliver the two duplicate pairs.
- The EPS continuation contains nested textblock
  `F_5f13328d-edbc-4a10-931c-876f58cddf90` and 12 numeric occurrences (three
  reconciliation rows, four periods). The final manifest must enumerate those
  IDs if full preservation is required. Parent context must not overwrite the
  child periods; the nested table alone does not deliver the computation body
  or its continuation edge.

The final machine manifest must separate ordinary financial evidence requirements
from delivery controls. Each acceptable alternative needs a complete role map:
AND within an alternative, OR between complete alternatives. Partial alternatives
must not be combined into a passing packet. Requirements/budgets freeze before
candidate question execution and scoring, with prior baseline exposure disclosed.
