# Document navigation development results

November 23, 2026. Full comparisons are still in progress.

The quick25 development loop improved numerical coverage while reducing estimated
cost. The second treatment is selected for the full comparison; this pilot alone
does not establish full-suite or production reliability.

| Measure | Fresh baseline | First treatment | Selected second treatment |
|---|---:|---:|---:|
| Exact numeric matches | 4/25 (16%) | 9/25 (36%) | 9/25 (36%) |
| Within 1% | 6/25 (24%) | 11/25 (44%) | 12/25 (48%) |
| Numeric answers | 7 | 12 | 16 |
| Quote-valid numeric answers | 7 | 12 | 16 |
| Abstentions | 9 | 9 | 9 |
| Stops or failures | 9 | 4 | 0 |
| Estimated model and search cost | $1.083 | $0.856 | $0.801 |
| Sum of task runtime | 410 seconds | 409 seconds | 341 seconds |

The comparison uses the same 25 questions, corrected references, model, six-model-call
limit, eight-tool-call limit, 90-second task timeout, 1,800 output-token cap and
$0.12 task ceiling. Each policy receives one attempt per question. The November 20
results remain historical records; they were not substituted for this fresh
baseline. Two preliminary launches failed authentication before inference because
of an inherited credential; their setup failures are preserved separately.

The first treatment replaces inaccessible 16,000-character prefixes with larger,
bounded immutable snapshots, adds search within each document, and keeps evidence
reads short. It also prevents a new finder result from disappearing behind an
older large search in model context. The first comparison yielded six exact
fail-to-pass transitions and one pass-to-fail transition. Gains were not uniform.

Trace inspection then found that a 30-line clamp could cut off an already-located
row. The selected treatment permits up to 80 lines under a serialized-character
budget, reduces discovery text, exposes missing lexical query terms, and instructs
the model to read promising matches before spending more turns on finding.
This iteration removes observed execution stops, but four of its sixteen
numerical answers still miss the 1% tolerance. Completing a response is not enough.

An independent coding-agent review of the first treatment found no clear
metric/period/unit failure among its nine exact matches. Two tolerance-only answers
used rounded source values. One captured source disagreed with the frozen reference;
the mismatch remains unchanged. This is agent inspection, not independent human
finance validation. Exact quote replay checks the text, not semantic support.

Review of the second treatment identified a confirmed cumulative-versus-quarterly
EPS substitution in SBI and a fiscal/calendar quarter mismatch in PayPay. Mitsui
and Lions Gate remain reference/period discrepancies that the captured evidence
does not settle. Kewpie's exact numerical match adds an unsupported calendar-period
gloss. No reference or numerical score was changed to hide these issues. Answer
coverage increased, but conditional tolerance matching fell from 11/12 numerical
answers in v1 to 12/16 in v2. The selected primary metric rewards all-question
success; it does not establish that v2 is safer for unreviewed financial use.

The treatment combines ingestion, navigation, context selection and instructions.
Live web results and provider nondeterminism remain confounders. Quick25 is exposed
development material used to select the treatment. The full comparison will report
the entire inventory and the nonreserved cases outside quick25 separately.

[First comparison](document-v1-quick-comparison.json) and
[selected-treatment comparison](document-v2-quick-comparison.json) preserve paired
outcomes, stops, tool counts, costs and submission hashes. The
[full selection protocol](full-selection-protocol.json) was frozen before the
selected full run. The [research and loop record](../../document-navigation-loop-2026-11-23.md)
documents sources, rejected approaches, reservation boundaries and decision rules.
