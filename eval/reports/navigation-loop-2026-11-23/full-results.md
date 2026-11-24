# Full navigation and finance benchmark results

Experiment date: November 23, 2026. Both full retrieval runs are finished.

The revised document-navigation treatment improves numerical matching on the full
eligible Daloopa selection, including questions outside the quick pilot, while
reducing estimated cost. It does not establish reliable financial interpretation:
more than half of scorable questions still fail the 1% threshold, and fiscal-period
and table interpretation remain known weaknesses.

## Full retrieval comparison

Each arm attempted all 499 eligible questions in the fixed 500-question inventory.
One reserved issuer remains a placeholder; 73 references remain unresolved and
are excluded from numerical grading, leaving 426 scorable questions. No reference
was changed to improve this comparison.

| Measure | Baseline | Document v2 |
|---|---:|---:|
| Exact numerical matches | 144/426 (33.8%) | 178/426 (41.8%) |
| Within 1% | 164/426 (38.5%) | 199/426 (46.7%) |
| Numerical answers, including unresolved references | 233/499 | 290/499 |
| Completed abstentions | 199 | 145 |
| Completed responses | 432 | 435 |
| Stops or failures | 67 | 64 |
| Quote-valid numerical answers | 233/233 | 290/290 |
| Estimated model/search cost | $20.824 | $14.653 |
| Sum of task runtime | 8,115 seconds | 6,883 seconds |

The primary 1% result improves by **8.2 percentage points**, with **69 gains and
34 regressions** on matched questions. Exact matching has 69 gains and 35
regressions. Estimated cost falls 29.6%; summed task runtime falls 15.2%. Runtime
is the sum of individual task measurements, not elapsed experiment wall time.
Costs are application estimates, including retained uncertain reservations, not
verified provider invoices.

Outside the quick25 used for development selection, 474 questions were eligible
and 401 scorable. Within-1% matches rise from **156/401 (38.9%) to 189/401 (47.1%)**;
exact matches rise from 140 to 171. The tolerance comparison has 65 gains and 32
regressions. This supports a broader improvement than the pilot, but these are
public development questions, not guaranteed unseen issuers or model-held-out data.

The quick25 slice inside this full run is a fresh attempt: within-1% results are
8/25 versus 10/25. The earlier pilot's 6/25 versus 12/25 remains a separate result;
we do not substitute whichever attempt scores better.

## What changed, and what still fails

The treatment retains larger immutable document snapshots, finds relevant ranges
inside a source, reads bounded surrounding context, and preserves recent evidence
in model context. Search requests fall from 1,375 to 901; explicit reads fall from
1,312 to 666, with 996 local finding calls. This is evidence for the combined
navigation treatment, not proof of the contribution of any one component.

Context-size stops fall from 17 to zero, and model-call-limit stops fall from 17
to 14. However, output-length failures rise from 30 to 45. Rejected citation-quote
failures rise from one to four. Those invalid answers are blocked and retained as
failures; zero invalid quotes among completed numerical answers does not mean
zero citation-generation errors. Overall execution failures improve only slightly.

Semantic review already found cumulative EPS used for a standalone quarter and
calendar/fiscal-period confusion. Flattened tables can detach values from their
headers. Quoting source text exactly does not resolve either issue. The source
review and unresolved reference discrepancies are preserved in
[semantic review](semantic-review.md); they were not used to retune the frozen
full-run policy. This review is agent inspection, not independent human validation.

## Existing finance suites and reasoning experiment

These are the complete eligible **prepared development subsets**, not complete
publisher releases. They supply documents/questions directly and do not exercise
web navigation. Each of the original and precision-guided arms selected 201 tasks.

| Suite | Original instructions | Precision guidance |
|---|---:|---:|
| CFA Easy | 65/70 | 66/70 |
| CFA Challenge | 25/30 | 25/30 |
| FinQA, 2,000 output tokens | 50/96 | 59/96 |
| TAT-QA previously exposed controls | 4/4 | 4/4 |

FinQA selects 97 tasks with one unresolved reference excluded from grading; three
reserved LMT tasks remain excluded. TAT-QA is restricted to four previously exposed
controls: the other 96 issuer identities are unresolved. Four passes are not
representative TAT-QA validation. All eight saved suite scores reproduce exactly.

The separate FinQA 2×2 experiment distinguishes instruction quality from output
allowance. Original instructions score 50/96 at 2,000 tokens and 47/96 at 4,000;
precision guidance scores 59/96 and 64/96 respectively. Guidance plus 4,000 tokens
is the strongest measured FinQA setting, but costs $0.400 versus $0.289 for guided
2,000 tokens. More output alone is not a general remedy. See the
[complete factorial comparison](finqa-output-comparison.json).

## Integrity and interruptions

Both arms use the same prepared references, model, six-model-call/eight-tool-call
limits, 90-second timeout, 1,800 output-token cap and $0.12 per-task ceiling.
Selection was frozen before the candidate full run. Provider allowance failures
interrupted both arms; a later connection failure interrupted the baseline.
Continuation executed only untouched questions in new directories. All dispatched
outcomes, including failures, remain unchanged; conservative cost reservations
remain accounted for. The original stopped submissions remain available.

The final audit reproduced both saved scores, checked all 11 recorded runtime
module hashes per arm, verified original submission hashes and immutable prior
records, and confirmed all 499 eligible attempts are terminal with the reserved
placeholder intact. [Integrity evidence](full-integrity.json) records these checks.

The primary denominator includes infrastructure failures. A secondary sensitivity
check excludes the union of three provider-interrupted question IDs from both
arms: within-1% matching is 164/423 versus 198/423. The gain persists. This does not
replace the main result or justify retrying failed questions.

Live search changes, provider nondeterminism, one attempt per policy, and the
combined intervention limit causal interpretation. No human-supported accuracy
or production-readiness claim follows from numerical or quote matching.

## Decision and next experiment

Retain document v2 as the preferred measured retrieval experiment, with baseline
available and defaults unchanged. It achieves more correct numerical answers at
lower estimated cost. Do not treat it as an autonomous financial verification
system. Retain precision guidance and the optional larger output budget for the
separate supplied-document task; do not silently apply it to this retrieval result.

The next justified hypothesis is explicit fiscal-period and table-header evidence
alignment, followed by a separately frozen comparison. Native table extraction
needs its own acceptance evidence: the tested Exa HTML option returned no table
structure, so that approach was not adopted. Output truncation also warrants a
retrieval-specific controlled experiment; the FinQA result does not establish its
benefit here. No further full-run tuning or best-of reruns were performed in this
round.

[Machine-readable paired results](full-comparison.json) retain all transitions,
group denominators, tool counts, costs, and final submission hashes.
[Research, implementation decisions, and protocol](../../document-navigation-loop-2026-11-23.md)
document the two navigation iterations and the reasoning/output-budget loop.

## Completion verification

Final `yarn lint` and `yarn test` passed (653 tests). The suite includes document
access/citation boundaries, Unicode transport sizing, context projection, paired
comparison policy checks, and immutable continuation behavior. Some tests emitted
SQLite resource warnings; the run completed successfully.

The completed scope is the documented round: recent primary-source research;
two implemented navigation versions; measured quick selection followed by frozen
full eligible retrieval; complete eligible prepared finance controls; a separate
prompt/output-budget factorial experiment; preserved evaluation reservations;
and reproducible results with an explicit decision. Research citations and
rejected approaches remain in the linked research record. No protected validation
content was opened for tuning, and no production-readiness claim is made.
