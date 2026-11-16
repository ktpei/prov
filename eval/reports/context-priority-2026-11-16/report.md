# Earlier-read preference recovers the inspected retention losses

Under the same 32,000-character limit, the fixed challenger preserves complete
annotated read packets for **1/3, 2/3 and 2/3 cases** at one, three and five reads.
The exact historical baseline remains **1/3, 2/3 and 0/3**. At five reads there are
**two wins, zero losses and one tie**; earlier cutoffs have three ties each.

Implementation `2014ea3`, freeze `6756e7a`. The [plan](plan.md), [protocol](protocol.json),
[summary](summary.json) and [receipt](receipt.json) bind the comparison. Baseline
output bytes exactly reproduce the earlier result. The original runtime, input
protocols, annotations and saved tool responses remain unchanged. Production
context behavior is unchanged; the challenger is an experimental artifact.

| Case, five reads | Baseline retained ranks | Challenger retained ranks | Baseline → challenger characters | Complete packet change |
| --- | --- | --- | ---: | --- |
| Walmart | 3, 4, 5 | 1, 2, 5 | 26,533 → 30,638 | No → No |
| NIKE | 3, 4, 5 | 1, 2, 5 | 25,481 → 27,713 | No → Yes |
| Ulta | 2, 3, 4, 5 | 1, 2, 3, 5 | 28,921 → 25,833 | No → Yes |

The sole selection change tries optional non-search results oldest-first, after
protecting the latest search and read. All nine challenger snapshots fit; none
blocks. Read call/output order and exact strings remain intact. No extra read,
search, semantic scoring or evidence-label input is added by the policy.

NIKE recovers its statement identity, period/scale and three cash-flow totals
across multiple retained reads. Ulta recovers the complete five-role packet in
its first read. Walmart still misses the required statement evidence because its
retrieval failed upstream. The challenger cannot create evidence absent from
selected sources. Ulta remains the only single-read-complete case.

## Interpretation and verification

This is a targeted experiment after inspecting the baseline failure. Earlier reads
correspond to higher retrieval ranks in this fixed schedule; that relation does
not hold for arbitrary agent histories. The synthetic discriminating test shows
the actual tradeoff: one policy preserves an earlier optional result, the other a
later one. Neither generally dominates. No default promotion follows from three
exposed public development cases. Fresh evaluation is needed before adoption.

These are independent synthetic-history snapshots, not model trajectories or
financial answer scores. The unchanged posthoc packets do not establish semantic
sufficiency or human annotation validity. Ulta's fiscal-year convention remains
unresolved. Counts use serialized tool-output-string characters, not tokens,
prompt-wide limits or JSON bytes.

The wrapper runs baseline first, so that process has accessed annotations before
the challenger executes. The projector's inputs are strictly messages and budget;
this is a data-flow boundary, not a process-wide claim that labels were unopened.
The derived result identifies the older contract as its input-integrity protocol
and the new outer protocol as the policy/experiment authority. The local override
is restored on success or interruption; the shared production module is untouched.

There were 30 verification read calls and 12 verification searches across the two
conditions, zero paid model calls and no new agent policy decisions. Spending
remains $0.4814193. All 310 tests and lint pass. Independent implementation review
found an output-mutation gap; both condition outputs are now checked against their
expected bytes before completion, with regression tests for tampering and aborts.

Independent saved-artifact review recomputed paired counts, per-role coverage and
character budgets, verified frozen bindings and byte-identical baseline replay,
and confirmed that canonical-history hashes agree between conditions. It did not
perform additional projections or independently reconstruct full histories.
