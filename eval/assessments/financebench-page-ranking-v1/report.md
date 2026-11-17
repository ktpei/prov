# Page-context ranking result — 2026-11-16

**The challenger regressed and is not promoted.** At five reads it retains complete
frozen packets for **0/6**, versus the control's **1/6**, under both context
priorities: zero wins, one loss and five ties. At one/three reads both remain 0/6.
The loss is Costco. No failed/truncated reads or blocked projections explain it.

The [protocol](protocol.json) was committed at `07b10e0` before the first real
query, after the independently reviewed runner at `1e52d21`. Both conditions replay
exactly before packet grading. Historical compact control search/read payloads,
journals and context projections match exactly. [Result summary](result.json)
binds the protocol, raw run, receipt, telemetry and grade by SHA-256.

| Frozen-location measure | Control @1 / @3 / @5 | Page ranking @1 / @3 / @5 |
| --- | --- | --- |
| Selected parent opportunity | 0/6 · 0/6 · 1/6 | 0/6 · 0/6 · 0/6 |
| Search snippets delivered | 0/6 · 0/6 · 0/6 | 0/6 · 0/6 · 0/6 |
| Actual reads delivered | 0/6 · 0/6 · 1/6 | 0/6 · 0/6 · 0/6 |
| Retained, newest-first | 0/6 · 0/6 · 1/6 | 0/6 · 0/6 · 0/6 |
| Retained, earlier-first | 0/6 · 0/6 · 1/6 | 0/6 · 0/6 · 0/6 |

## Candidate limitation and observed change

The shared pool of 25 candidates contains complete frozen packets for **2/6**:
Costco and American Water Works. The other four cannot achieve complete *frozen
location* coverage by reordering this fixed pool alone. This is not a conclusion
that all semantically sufficient alternatives are absent; annotations are known
not to exhaust all potentially supporting locations.

Costco replaces control's L1185–L1216 with L1484–L1497, dropping the previously
complete asset evidence. American Water Works also swaps one window without
achieving completeness. The other four selected window sets remain the same,
though order may change. All 28 shared windows have identical read responses.
Neither whole-page ranking context nor unused pool candidates count as delivered
text. Pool completeness does not establish deliverability within five reads.

## Work, cost and operational checks

One shared passage-scoring pass and one page-scoring pass ran for each of six
cases: 1,715 eligible passages and 981 physical pages in total. These produced 12
derived search responses and 60 reads (30 per branch). Exact verification repeated
that shared work and 60 reads, for 120 original-plus-replay read attempts. There
were no failures or truncations. Every prefix/policy projection was unblocked.
No paid inference, provider calls, new acquisition or validation-content access.

Using the existing context cost definition—serialized JSON **output-string**
characters including escaping—control reads total 250,316 characters and challenger
reads 245,094. Searches add 32,850 and 32,689 respectively. Count each response once;
do not multiply by context policies/prefixes. These are not tokens, bytes or total
prompt lengths. The control reproduces the preceding compact assessment's sizes.

Recorded original-run scoring time is approximately 0.302 seconds shared by the
branches. Read regions total 0.597 seconds for control and 0.591 for challenger.
These local, one-run observations exclude corpus construction and context projection;
they do not establish a speed advantage. Timing is separately hash-bound and not
claimed to replay exactly. Both conditions share scoring work; do not count it as
two independently executed searches or claim equal caps imply equal cost.

## Interpretation and next work

Keep default retrieval unchanged. Preserve this failed ablation and its frozen
parameters; do not adjust the constant after seeing these outcomes. The result
supports diagnosing candidate recall and financial information needs separately
from ranking, while independently auditing annotation alternatives. Any new query
policy needs its own prospective protocol and permitted inputs that exclude gold
pages, evaluator roles, formulas and reference-derived operand lists.

This is a six-case exposed development diagnostic. Frozen-location matching is not
financial correctness, exhaustive semantic sufficiency or human validation. The
3M metric ambiguity/possible alternative evidence and other prior annotation
caveats remain; no packets or historical scores were rewritten. The separately
reserved validation documents remain closed, with their two prior-issuer exposure
slots retained and disclosed. Original 25 tasks/15-task holdout remain unchanged.
