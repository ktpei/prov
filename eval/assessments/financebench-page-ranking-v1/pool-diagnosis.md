# Saved-pool diagnosis — 2026-11-16

This is post-hoc, evaluator-only analysis of the already replay-verified candidate
pools. It uses frozen evidence labels and performs no new search, ranking,
`read_source`, inference or acquisition. It is not a candidate-selection policy and
does not change any experiment score or packet.

## Exact window opportunity

| Case | Entire pool | Minimum parent windows within five | Original pool ranks |
| --- | --- | --- | --- |
| Costco | Complete frozen locations | 1 | 5 |
| American Water Works | Complete frozen locations | 2 | 2, 7 |
| Verizon | Missing required frozen locations | No witness | — |
| Coca-Cola | Missing required frozen locations in both alternatives | No witness | — |
| 3M | Missing required frozen locations | No witness | — |
| Johnson & Johnson | Missing required frozen locations | No witness | — |

Costco's single window is L1185–L1216. The control delivered it at rank five; the
page-ranking challenger dropped it. American Water Works can cover its complete
frozen packet with L2939–L2970 and L2887–L2918, at original pool ranks two and seven.
Neither method selected the latter among its five reads. This demonstrates selection
headroom under the frozen-location objective, not that a gold-free selector can
find the two-window combination or that it would fit a particular retained history.

Verizon's pool covers its revenue roles but lacks the annotated balance-sheet
identity, date/units and total-assets lines. Coca-Cola lacks its annotated income
and balance-sheet roles under both net-income alternatives. 3M lacks its five
annotated page-25 roles; previously observed alternative segment tables remain an
unadjudicated semantic possibility. Johnson & Johnson lacks all six annotated
inventory/earnings roles. Exact missing lines per role and alternative are recorded
in [the diagnosis](pool-diagnosis.json); they must not become retriever query terms,
training examples or validation annotation hints.

No case has a complete pool that requires more than five windows. The four failures
are missing-location problems within this fixed pool, not proof that the read cap
is too small. Reordering alone cannot recover these exact missing locations.

## Method and boundaries

The [diagnostic](diagnose_pool.py) binds the saved grade, deterministic run inventory,
frozen protocol and corpus/packet identities. It verifies ordered integer candidate
ranks and reuses strict pool/packet validation. It then enumerates subsets of size
one through five, evaluating exact required-line unions separately for every
alternative. It never fills gaps between windows or mixes alternatives. Within
an alternative, the first successful subset is minimum-cardinality, with original
rank tuples breaking ties; case-level ties then use alternative index. Unmapped
or unresolved cases cannot produce a zero-window pass.

The search is bounded at five. A complete pool with no such witness would receive
an explicit greater-than-five status, not an invented exact minimum. Required lines
can be split across multiple windows, including within one role. Four synthetic
tests cover minimum-size/lexical ties, gaps, disjoint evidence, the five-window
bound, candidate 25, empty evidence/pools and oversized inputs.

Witnesses establish parent-window opportunity only. Actual reads could truncate,
fail or omit context, and context projection could discard delivered results.
The 32K output-character limit is not modeled by this oracle. Existing annotations
also remain incomplete semantic judgments, with unresolved financial conventions.
Using this diagnosis to motivate development changes is label-informed analysis;
it supplies no validation generalization claim. All reserved validation content
remains closed, and historical results remain immutable.

The next useful work is a separately frozen, blinded alternative-evidence audit,
alongside gold-free candidate-generation research. Do not tune ranking constants
or write queries using these witness locations and role deficits.

Independent [audit](pool-diagnosis-audit.json) reproduced the diagnostic bytes and
confirmed both minimum witnesses using a separate exhaustive set-union calculation.
All 373 repository tests and lint pass. No original retrieval or grading was rerun.
