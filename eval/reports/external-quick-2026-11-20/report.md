# Quick external benchmark results — 2026-11-20

| Benchmark | Selected | Returned answers | Result | Estimated cost |
|---|---:|---:|---|---:|
| CFA-Easy | 5 | 5 | 5/5 choice matches (100%) | $0.0013194 |
| CFA-Challenge | 5 | 5 | 4/5 choice matches (80%) | $0.0064464 |
| FinQA reviewed | 6 | 4 | 2/5 scorable cases (40%); 1 reference unresolved | $0.0127842 |
| TAT-QA reviewed | 4 | 4 | 4/4 exact match; F1 1.0; scale 4/4 | $0.0035040 |

Total: **20 selected, 19 model attempts, 18 returned answers**, $0.0240540
estimated cost. No uncertain-billing flags or batch retries. No blended accuracy
is reported across heterogeneous tasks. These small, exposed development samples
do not establish full-suite or production accuracy.

FinQA's five scorable cases include two correct scalar answers, two incorrect
scalar answers (ABMD/2006 and TROW/2010), and one output-length failure (IPG/2008).
MRO/2007 remained unscored and received no model request because its reference is
unresolved; it was not silently replaced. The scorer correctly keeps overall
six-case accuracy null. FinQA uses adapted scalar matching, not official program
or execution accuracy. One CFA-Challenge choice did not match its reference.
These labels describe frozen scorer outcomes, not a new human financial review.

Model: `deepseek/deepseek-v4.1-flash-1017`; supplied-context FinQA/TAT-QA and
model-only CFA questions. Each eligible question received one request, 2,000
maximum output tokens and a 60-second timeout. Pricing estimates use $0.60/$2.40
per million input/output tokens. Selection and a $0.40 aggregate ceiling were
recorded before dispatch in [protocol.json](protocol.json). The first fixed
seeded cases from each existing prepared development set were selected; later
failures did not change selection.

All four saved scores reproduced exactly offline. The original heldout set and
reserved FinanceBench issuer content were not evaluated. Existing TAT-QA cases
have prior annotation caveats, so official metric matches are not independent
source verification. No Daloopa retrieval result is inferred from these scores.

[Summary](summary.json) contains the totals. Raw submissions, prepared references,
answers and scores remain under `runs/external-quick-2026-11-20/` to avoid
redistributing third-party benchmark data. The protocol records their paths and
prepared identities; runtime files were hashed before inference. Concurrent
Office.js work changed the shared checkout but not these benchmark runtime files.
