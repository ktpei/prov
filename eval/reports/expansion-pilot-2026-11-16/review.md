# Independent coding-agent expansion-pilot review — 2026-11-16

This review diagnoses saved outputs against their supplied context and evaluator
references. It is **coding-agent analysis, not independent human financial
validation**. No inference, retries, score changes, source-registry changes, or
runtime changes were performed for this review. All original outcomes remain
frozen, including both conversation conditions' failed turns.

## Frozen outcomes and execution identity

| Condition | Completion | Original scoring | Accounted cost |
| --- | ---: | --- | ---: |
| TAT-QA, supplied context | 4/4 questions | Official EM 1.0, F1 1.0, scale accuracy 1.0 | $0.0035376 |
| ConvFinQA, agent history | 9/9 turns; 2/2 conversations | 6/9 turns; 0/2 whole conversations | $0.0131154 |
| ConvFinQA, reference history | 9/9 turns; 2/2 conversations | 6/9 turns; 0/2 whole conversations | $0.0124002 |

Total accounted cost is **$0.0290532**. All 22 task/turn records have
`cost_uncertain=false`; row costs reconcile with their batch totals to floating
point precision. These are conservative token-rate estimates, not invoices.
There was no recorded incomplete, malformed-output, budget-stop, or uncertain-cost
failure in these batches. Scoring discrepancies are separate from completion.

The [preregistered protocol](protocol.json) identifies runtime code commit
`79d5376ae5f7e8778d32a21ee15441927dcdc40a`. The submissions identify clean commit
`17ee7a48b027fa616dac1a8a9cbad7de810cf606`; the only changed path between those
commits is the protocol itself. The recorded model is
`deepseek/deepseek-v4.1-flash-1017`, temperature 0, 2,000 maximum output tokens,
zero automatic retries, and default OpenRouter routing. This is a small public
development diagnostic with an adapted prompt, not a complete official evaluation.

## Sources and retained artifacts

- TAT-QA development release, revision
  `870accc41953dcde885aabeb963d94aabdc0fbc3`,
  [pinned JSON](https://raw.githubusercontent.com/NExTplusplus/TAT-QA/870accc41953dcde885aabeb963d94aabdc0fbc3/dataset_raw/tatqa_dataset_dev.json),
  source SHA256 `8da095a819af6db3c14877c6df2d4d29960e41d1a63dd1fa853507bd2a616af5`.
- ConvFinQA development release, revision
  `cf3eed2d5984960bf06bb8145bcea5e80b0222a6`,
  [pinned archive](https://raw.githubusercontent.com/czyssrs/ConvFinQA/cf3eed2d5984960bf06bb8145bcea5e80b0222a6/data.zip),
  archive SHA256 `d764271fae60d81b62e6d58dfc481807ebc8cfbcd633811241723c4a2101072a`;
  original `data/dev.json` member SHA256
  `9665dd60f106e5cd41d37537edac97bbd26eb7629ad63ca2390b19d4619ba51b`.

The source hashes identify dataset bytes, not independently verified original
filing contents or table geometry. TAT-QA supplies context-group identifiers,
not original-document page locators.

Local artifacts are retained under ignored `runs/` storage:

- TAT-QA: [evaluator tasks](../../../runs/expansion-pilot-2026-11-16/prepared/tatqa/tasks.json),
  [submission](../../../runs/expansion-pilot-2026-11-16/results/tatqa/submission.json),
  [original score](../../../runs/expansion-pilot-2026-11-16/results/tatqa/score.json).
- ConvFinQA agent history: [evaluator tasks](../../../runs/expansion-pilot-2026-11-16/prepared/convfinqa-agent/tasks.json),
  [submission](../../../runs/expansion-pilot-2026-11-16/results/convfinqa-agent/submission.json),
  [original score](../../../runs/expansion-pilot-2026-11-16/results/convfinqa-agent/score.json).
- ConvFinQA reference history: [evaluator tasks](../../../runs/expansion-pilot-2026-11-16/prepared/convfinqa-reference/tasks.json),
  [submission](../../../runs/expansion-pilot-2026-11-16/results/convfinqa-reference/submission.json),
  [original score](../../../runs/expansion-pilot-2026-11-16/results/convfinqa-reference/score.json).

## TAT-QA: official matches and evidence diagnosis

### `197c37a3-cd56-4eef-bccc-756f88753971`

**Classification: supported textual extraction and official match.** Context group
`fa0d7378-4217-44f1-bfb0-38688f03bdf3`, paragraph order 3
(`004c0a28-f9b0-4a9a-8bf2-4bdd8423bec8`), directly identifies the two components
of the pro-forma adjustments: acquired-inventory fair-value costs and purchased
intangible amortization. The returned phrase matches that finding; scale is empty.
This does not assert that the pro-forma results were actual realized results.

### `0339e2bb-4a63-4f23-aaea-b9fa3cb29737`

**Classification: supported table arithmetic and official match.** Context group
`ae44e24d-3fb5-4eff-95e1-ec8fc530c1d7` gives 381 ground leases and 697 land/building
leases in the FY2020–2024 expiration row. The difference is `697 − 381 = 316`,
matching the returned number and gold derivation. Empty scale is appropriate for
the count difference.

### `94ef7822-a201-493e-b557-a640f4ea4d83`

**Classification: supported table arithmetic and official match.** Context group
`8692f92d-668a-452d-be7a-2b491ee27585` labels total current tax expense in EUR
millions: 950 for 2017, 1,018 for 2018, and 1,062 for 2019. The two averages are
`(950 + 1018)/2 = 984` and `(1018 + 1062)/2 = 1040`; their change is
`1040 − 984 = 56` million. The returned value and scale agree.

### `d3dc2462-fd1b-4871-a0f6-6b4837100c05`

**Classification: official numeric match with a metric-label concern requiring
adjudication.** Context group `9b0abd12-8d9e-48ba-9ac2-baacfa92e7eb` contains cloud
row amounts of 67,918 and 45,218, denominated in thousands. Their average is
`(67918 + 45218)/2 = 56568`, exactly matching the returned answer and gold.

However, the question describes cloud revenue, while paragraphs at orders 1 and
3 identify gross profit, order 5 identifies gross-profit percentage, and order 6
discusses changes in cloud gross-profit percentage. The table pairs the cloud
amounts with 51% and 55% margins. This supplied context indicates a gross-profit
table, so averaging its amounts does not establish the requested revenue figure.
The official pass is preserved; it must not be presented as independently verified
financial correctness. Review the original source and annotation before deciding
how a future assessment should treat this example.

## ConvFinQA: paired history conditions

Turn indices are zero-based. Both conditions use the same two conversations and
the same nine gold targets. The same three turns fail in both conditions; reference
history does not improve the aggregate result on this tiny paired sample.

### `Single_GS/2017/page_143.pdf-1`

Source locator: `GS/2017/page_143.pdf`, the credit-net row, with dollar amounts in
millions and columns for December 2017 and December 2016.

| Turn | Evaluator target | Agent-history output | Reference-history output | Frozen result |
| --- | ---: | ---: | ---: | --- |
| 0 | 1505 | 1505 | 1505 | Pass in both |
| 1 | 2504 | 2504 | 2504 | Pass in both |
| 2 | -999 | -999 | -999 | Pass in both |
| 3 | 2504 | 2504 | 2504 | Pass in both |
| 4 | -0.39896 | -999 | -999 | Fail in both |

**Classification:** the first four turns correctly extract the source values and
calculate `1505 − 2504 = -999`. The final gold program divides that change by the
2016 base: `-999 / 2504 = -0.398961661…`, rounded to `-0.39896`. Both responses
repeat the absolute change rather than performing that additional division.
This is a requested-operation/relative-change interpretation discrepancy, not a
wrong extraction of either source amount. The wording asks for change over the
2016 value; the evaluator interprets that as relative change. Correct prior
history was already available in both conditions, so this case does not show an
error propagated from a wrong earlier answer.

### `Double_GPN/2009/page_70.pdf`

Source locator: `GPN/2009/page_70.pdf`, FY2008 acquisition allocation table in
thousands, plus the second post-table text entry describing contract-based
intangibles' amortization range.

| Turn | Evaluator target | Agent-history output | Reference-history output | Frozen result |
| --- | ---: | ---: | ---: | --- |
| 0 | 1031 | 1031 | 1031 | Pass in both |
| 1 | 103.1 | 158.6 | 158.6 | Fail in both |
| 2 | 13536 | 13536 | 13536 | Pass in both |
| 3 | 0.69676 | 69.7 | 69.68 | Fail in both |

**Turn 0 and turn 2: supported extraction.** Contract-based intangible assets are
1,031 thousand, and goodwill is 13,536 thousand. Both conditions return those
amounts correctly.

**Turn 1: unstated amortization assumption requiring adjudication.** Gold divides
1,031 by 10 years, obtaining 103.1 thousand per year. The supplied text instead
gives a 3–10-year amortization range for this class of assets; it does not establish
a single life or allocation across lives for the full 1,031. The returned 158.6
is consistent with dividing by the range midpoint: `1031 / 6.5 = 158.61538…`,
rounded to one decimal. This is an inference about a possible calculation, not
evidence of the model's internal reasoning. Neither the midpoint assumption nor
applying the upper endpoint to all these assets is uniquely established by the
provided evidence. A separate Canadian agreement described later has a ten-year
life, but that statement does not establish a ten-year life for the complete
1,031 allocation. Do not recast this as a straightforward arithmetic mistake or
silently replace the reference.

**Turn 3: percentage-versus-execution-ratio mismatch, with precision loss.** The
source gives total assets acquired of 19,427 thousand. Gold computes
`13536 / 19427 = 0.696762238…`, rounded to `0.69676`. Expressed as a percentage,
this is approximately 69.6762%. The model's 69.7 and 69.68 are sensible rounded
percentage magnitudes, but neither is the required raw execution ratio. Even
dividing those already rounded answers by 100 would give 0.697 and 0.6968, which
still differ from the frozen five-decimal target. Preserve both strict failures;
do not apply post hoc percent conversion or a looser tolerance.

The reference-history run supplies 103.1 as the prior answer after turn 1; the
agent-history run supplies its own 158.6. Both then extract goodwill correctly,
and both produce a percentage magnitude at the last turn. The modest rounding
difference does not establish a causal benefit from reference history.

## Interpretation and adjudication queue

The ConvFinQA output contract requests a number or yes/no in execution-result
scale. It does not explain with examples that a natural-language percentage
question can have a ratio-valued execution target. These results therefore mix
financial interpretation, output-scale adaptation, and precision requirements;
they are not a clean estimate of finance knowledge alone. The strict scalar
contract also offers no structured route to qualify an ambiguous useful life.
Any future prompt or scoring adaptation needs a new version and preregistration,
not reinterpretation of this pilot's outputs.

Before later assessment, adjudicate the TAT-QA cloud revenue/gross-profit label,
the GPN asset-life assumption, and the handling of percent-valued language versus
execution-scale targets. Keep the original 4/4 official matches and both 6/9
turn scores visible alongside these concerns. No replacement adjusted accuracy
is assigned here. The inspected tasks are development/regression material.

No full-document retrieval, PDF extraction fidelity, human financial validation,
or broad generalization was established. Public-source overlap, four TAT-QA
questions, and two conversations per condition prevent strong comparative claims.
