# Independent coding-agent pilot review — 2026-11-16

This is an independent coding-agent diagnostic of saved FinQA and FinanceBench
pilot outputs, supplied evidence, and evaluator references. It is **not human
financial adjudication**, an official benchmark score, or a general accuracy
estimate. No inference, retries, runtime changes, or score changes were performed
for this review. The original 15-task holdout was not inspected.

The reviewed submissions record runtime commit
`ff93a7faf9b3a5c182af5aa4886cc6f2efa57775`, a clean working tree,
`deepseek/deepseek-v4.1-flash-1017`, temperature 0, 2,000 maximum output tokens,
zero automatic retries, and default OpenRouter provider routing. FinQA used
supplied context; FinanceBench used supplied answer-bearing evidence without
the gold answer or justification. These are not retrieval evaluations.

## Frozen outcomes and source identities

| Dataset | Original result | Source identity |
| --- | --- | --- |
| FinQA, development split | 3 selected; 2 scalar/yes-no passes; 1 incomplete; adapted answer-only accuracy **2/3** | Revision `0f16e2867befa6840783e58be38c9efb9229d742`; downloaded bytes SHA256 `a847fb7e0d61a3125a1e2909852df6b89f1ee64d2c5ff1bf689e332214deee51` |
| FinanceBench, public sample | 2 selected; 2 completed; 2 pending semantic reviews; automatic accuracy **null** | Revision `cc39aeb4afdf33909ee1412188bf89035950c2eb`; downloaded bytes SHA256 `a5a2aa673e573e55675fc3c0f9aa38c1cf59d2abc91edb077534f71f10a71877` |

Pinned upstream sources: [FinQA dev.json](https://raw.githubusercontent.com/czyssrs/FinQA/0f16e2867befa6840783e58be38c9efb9229d742/dataset/dev.json)
and [FinanceBench public JSONL](https://raw.githubusercontent.com/patronus-ai/financebench/cc39aeb4afdf33909ee1412188bf89035950c2eb/data/financebench_open_source.jsonl).
These hashes identify dataset bytes, not independently verified original filings.

Local raw artifacts, retained under the ignored `runs/` directory:

- FinQA [submission](../../../runs/external-pilot-2026-11-16/results/finqa/submission.json),
  [frozen score](../../../runs/external-pilot-2026-11-16/results/finqa/score.json),
  [prepared evaluator records](../../../runs/external-pilot-2026-11-16/prepared/finqa/tasks.json),
  and [downloaded source](../../../runs/benchmark-data/finqa-dev/finqa-dev.json).
- FinanceBench [submission](../../../runs/external-pilot-2026-11-16/results/financebench/submission.json),
  [frozen score](../../../runs/external-pilot-2026-11-16/results/financebench/score.json),
  and [prepared evaluator records](../../../runs/external-pilot-2026-11-16/prepared/financebench/tasks.json).

The linked submissions and scores retain their prepared-manifest and input
hashes. Use those machine-readable identities when reproducing the saved scores.

## FinQA findings

### `MRO/2007/page_149.pdf-1`

**Classification: operational length-limit failure, with an upstream malformed or
underspecified question.** The supplied question is a table-row fragment rather
than an explicit request to average values. The exact same fragment occurs in the
downloaded upstream `qa.question`; the downloaded file hash matches the recorded
source hash. The adapter therefore did not introduce this question defect.

The evaluator's program requests the average of development costs across the
2007, 2006, and 2005 columns of `MRO/2007/page_149.pdf`:

`(1654 + 1251 + 1030) / 3 = 1311.666666…`, rounded to `1311.66667`.

The model produced no accepted final answer. The retained
`rejected_provider_response` has empty content, finish reason `length`, and usage
of 684 input / 2,000 output tokens. Its accounted charge is **$0.0052104**,
`cost_uncertain=false`. At $0.60/$2.40 per million input/output tokens,
`(684 × 0.60 + 2000 × 2.40) / 1,000,000 = 0.0052104`.

The record establishes a generation-limit failure, not an observed arithmetic
mistake. It does not establish why the model exhausted its output allocation.
Keep this failed attempt in the original denominator; do not remove or repair the
question retroactively to improve the saved score.

### `RSG/2015/page_142.pdf-1`

**Classification: evidence-supported scalar pass.** The permitted table in
`RSG/2015/page_142.pdf` gives 27,000,000 gallons hedged for 2016 and 12,000,000 for
2017. `27,000,000 / 12,000,000 = 2.25`, matching both the returned scalar and
evaluator execution result. Accounted cost: **$0.0007638**.

### `AES/2002/page_46.pdf-1`

**Classification: evidence-supported yes/no pass.** The permitted first-quarter
price table in `AES/2002/page_46.pdf` yields `17.84 − 4.11 = 13.73` for 2002 and
`60.15 − 41.30 = 18.85` for 2001. The returned `no` agrees with the requested
comparison and evaluator result. Accounted cost: **$0.0007254**.

All three FinQA charges reconcile to **$0.0066996**. Both returned answers are
correct under the adapted scalar contract; this does not measure program accuracy.

## FinanceBench findings

Page locators below follow the supplied **zero-indexed** evidence-page convention,
not necessarily the page numbers printed within the original filing.

### `financebench_id_00591` — Adobe FCF conversion

**Classification: evidence-supported answer in this coding-agent diagnostic;
human adjudication remains pending.** The response cites `ADOBE_2022_10K`, page 56,
whose supplied cash-flow excerpt contains the years, units, and every input used.

| Calculation | FY2022 | FY2021 |
| --- | ---: | ---: |
| Operating cash flow minus property/equipment purchases, USD million | `7838 − 442 = 7396` | `7230 − 348 = 6882` |
| Net income, USD million | 4756 | 4822 |
| FCF / net income | 155.5088% | 142.7209% |

The model's approximately 155.5% versus 142.7% and improving direction are
supported. The gold answer's approximately 13% improvement is imprecise: the
difference is **12.7880 percentage points**, or **8.9601% relative**. The response
does not repeat that ambiguity. No material unsupported addition was identified
in this short response against the supplied excerpt. Accounted cost: **$0.0035814**.

### `financebench_id_00540` — AES inventory turnover

**Classification: denominator-convention disagreement requiring adjudication,
not a simple arithmetic error or an automatic pass.** Both the model's inputs and
citations match the supplied `AES_2022_10K` excerpts: page 129 supplies 2022 and
2021 inventory of 1,055 and 604 million; page 131 supplies 2022 cost of sales of
10,069 million in magnitude.

- Model convention: average inventory `(1055 + 604) / 2 = 829.5`;
  `10069 / 829.5 = 12.1386`, reported as approximately 12.1 times.
- Gold convention, explicitly recorded in its justification: ending inventory;
  `10069 / 1055 = 9.5441`, reported as approximately 9.5 times.

Both calculations are arithmetically correct under their stated denominators;
the question does not specify which denominator to use. A gold-only comparison
would conflate a definition disagreement with a calculation error. Separately,
the response's interpretation as inventory being sold/replenished and the
economic suitability of this turnover measure are not established by these two
statement excerpts alone. The response notes the limits of supplied evidence,
but mere calculability does not settle suitability. Accounted cost: **$0.0029646**.

Both FinanceBench charges reconcile to **$0.006546**. Both responses have
`cost_uncertain=false`. These are conservative token-rate estimates, not invoices.
FinanceBench automatic accuracy remains null; this review does not replace either
pending semantic review with a scored pass or failure.

## Adjudication queue and limits

Before a later assessment, independently review malformed question handling,
explicit denominator conventions, percentage versus percentage-point wording,
and whether supplied evidence supports the economic interpretation requested.
Predeclare any exclusion or scoring policy before selecting new evaluation cases.
Retain this pilot's selected tasks, failed attempt, raw outputs, and scores exactly
as recorded. These inspected examples are now development/regression material.

No original filing/PDF geometry, full-document retrieval, independent human
financial judgment, or broad generalization was established by this review.
