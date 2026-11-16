# Table and conversation development pilot — 2026-11-16

The committed [protocol](protocol.json) selected four TAT-QA questions and two
ConvFinQA conversations (nine turns), with the same conversations run separately
under actual-model and reference history. All runs used clean commit `17ee7a4`,
`deepseek/deepseek-v4.1-flash-1017`, temperature zero, 2,000 output-token maximum,
and one attempt per task/turn. No repairs, retries, or uncertain billing occurred.

| Condition | Completion | Fixed-denominator result | Conservative cost |
|---|---:|---|---:|
| TAT-QA supplied context | 4/4 | EM 4/4; F1 1.0; scale 4/4 | $0.0035376 |
| ConvFinQA actual history | 2/2 conversations; 9/9 turns | 6/9 turns; 0/2 whole conversations | $0.0131154 |
| ConvFinQA reference history | 2/2 conversations; 9/9 turns | 6/9 turns; 0/2 whole conversations | $0.0124002 |

Total $0.0290532 against a $0.20 preregistered cap. Cumulative conservative
accounting is $0.4814193, leaving $0.5185807 of the authorized $1.00. These are
application estimates using $0.60/$2.40 per million tokens, not provider invoices.

All three score artifacts reproduced exactly from saved submissions. Local raw
artifacts are under `runs/expansion-pilot-2026-11-16`; [summary](summary.json)
records submission/score hashes. Original pilot and original 15-task holdout are
unchanged. Public benchmark data and full model traces remain local.

These tiny development samples do not establish benchmark-wide accuracy. ConvFinQA
uses adapted final scalar comparison, not official program accuracy. Both history
conditions failed the same turn indices; equal totals do not prove history quality
is irrelevant. Source-level review separates scale-convention failures and ambiguous
amortization assumptions from arithmetic mistakes. TAT-QA official matches also
require annotation review: a cloud-revenue question appears to reference a gross-profit
table. Preserve all original scores and report that distinction explicitly.

See [independent coding-agent review](review.md). This is diagnostic review,
not human financial validation or calibrated semantic adjudication.
