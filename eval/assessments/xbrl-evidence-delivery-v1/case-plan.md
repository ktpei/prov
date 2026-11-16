# Proposed development cases

Status: source-derived proposal, before candidate reader implementation/execution.
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
| ASR scope | Provide the amount and program scope of the ASR agreement entered into May 28, 2024. | Original line2844, F_7a65e687-9aaa-43aa-9c21-a2ca35d20104: 200.0 scale6, USD 200,000,000; instant May28,2024; ShareRepurchaseProgramAxis / AcceleratedShareRepurchaseAgreementMember. Surrounding narrative must distinguish agreement date, initial delivery and November settlement; the context date alone is not a settlement date. |
| Diluted EPS | Provide diluted EPS for the three and six months ended June 30, 2025. | Table-10 row34: 1.27 and 2.46, scale0, USD/shares. Require parent “Earnings per share:” at row32, “Diluted,” correct periods and the exception to the table's thousands convention. The baseline row34 read misses row32. A typed-concept alternative must be separately specified rather than silently equated with visible-label delivery. |
| Declared zero | What does the December 31, 2024 credit-agreement borrowings entry represent? | Table-15 row3, F_cafba24e-d3c2-4afd-aa16-d0e27d4640dc: em dash, declared fixed-zero transform, typed USD zero. Require period and row label. The glyph alone is not an unambiguous typed-zero basis. |
| Nil control | Distinguish the two commitments-and-contingencies nil facts from the zero borrowings fact. | F_d6d79b3b-30b4-41ee-97c3-4c6898ab25cf and F_4887bb55-57d5-47ad-a9e1-931d12ad9e68 are hidden, empty, xsi:nil=true at June30 and December31. Require nil/null, hidden disposition and original-element citations. This representation control does not establish that the company had no commitments. |
| Segment duplicates | Provide operating and reportable segment counts, accounting for repeated disclosures. | Original lines2729/3040: four nested occurrences, two concepts, each “one” to integer1 in unit Segment. Require two concept-specific duplicate pairs with retained citations. Do not sum repeated occurrences or conflate operating and reportable concepts. |
| Continuation | Provide the EPS computation disclosure together with its reconciliation continuation. | F_e962a1dd-89a6-466b-85ba-6a14dd973dd2 at original line2844 explains computation; continuation _1 at line2848 supplies reconciliation. Require both original fragments and their relationship, nested numeric occurrences, period/unit headers. Assembled text is not an original-byte quotation. |

Namespace-resolved concept, dimension and unit identifiers must be used in the
final manifest; short local names here are explanatory. Original line numbers
locate review material, not substitutes for byte/hash-bound citation identity.
Source-derived expectations were proposed by the independent methodology agent;
root directly verified the EPS parent-label gap. Remaining role alternatives and
financial sufficiency require case-by-case review before grading.

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
