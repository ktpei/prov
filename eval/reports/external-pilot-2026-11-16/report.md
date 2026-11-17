# External benchmark development pilot — 2026-11-16

Ten preselected tasks ran once on `deepseek/deepseek-v4.1-flash-1017` using the
[preregistered protocol](protocol.json), committed at `ff93a7f` before inference.
All runs recorded that clean Git revision. Runtime code was frozen at `b6dc09e`.
No runtime or scorer changes occurred during the batch; no retries or repairs ran.

| Dataset/condition | Selected | Completed | Adapted scalar/choice passes | Semantic status | Accounted USD |
| --- | ---: | ---: | ---: | --- | ---: |
| CFA-Easy, model-only | 3 | 3 | 3 | Choice accuracy only | 0.0008334 |
| CFA-Challenge, model-only | 2 | 2 | 2 | Choice accuracy only | 0.0020832 |
| FinQA, supplied context | 3 | 2 | 2 | One output-limit failure remains in denominator | 0.0066996 |
| FinanceBench, evidence supplied | 2 | 2 | Not scored | Two responses require semantic review | 0.0065460 |

No blended accuracy is reported. Five public multiple-choice questions do not
establish broad knowledge accuracy. FinQA **2/3** is the adapted scalar metric,
not official execution/program accuracy. FinanceBench automatic accuracy remains
null. Evidence supplied is an interpretation diagnostic, not a retrieval test.
No original holdout was run.

## What the review found

The [independent coding-agent review](review.md) preserves all original outcomes:

- The FinQA failure hit the 2,000-output-token limit. Its saved rejected response
  retains the finish reason, empty final content, usage, and known charge. Source
  inspection also found an underspecified upstream question: the gold program
  requests an average that the question does not clearly request. This cannot be
  treated as demonstrated arithmetic failure, but the attempt remains a failure.
- Adobe's FinanceBench response supports its cash conversion calculations from
  the supplied evidence. The gold explanation's percentage wording is imprecise;
  percentage points and relative improvement must stay distinct.
- AES's FinanceBench response uses average inventory while gold uses ending
  inventory. Both arithmetic results follow their respective conventions. The
  question does not resolve the convention, and some model commentary extends
  beyond the statement excerpts. This requires adjudication, not an automatic pass
  or simple arithmetic-error label.

This is a coding-agent diagnostic, not independent human financial validation.
It motivates explicit reference-issue tracking and better adjudication rubrics.
It does not justify silently changing gold values or removing failures.

## Cost and artifact integrity

Total conservative accounted cost: **$0.0161622**, below the **$0.15** pilot cap.
All ten attempts had `cost_uncertain=false`. Rates were $0.60/$2.40 per million
input/output tokens, conservatively above the current maximum published schedule.
Application accounting is not an invoice. Combined with prior recorded estimates,
accounted development spending is **$0.4523661** of the existing $1 authorization,
leaving **$0.5476339**. The account-side daily cap remains separate.

[Machine-readable summary](summary.json) records exact task IDs, input hashes,
submission/score file hashes, runtime revision, statuses, costs, and local artifact
paths. All original submissions, raw responses, prepared tasks, and input/reference
manifests remain under `runs/external-pilot-2026-11-16/`. These ignored files contain
third-party benchmark inputs and evaluator gold and are not redistributed here.
Use the pinned acquisition catalog and protocol to reconstruct the inputs.

Offline rescore, without further inference:

```sh
uv run python -m provenance.benchmarks score \
  --prepared runs/external-pilot-2026-11-16/prepared/finqa \
  --predictions runs/external-pilot-2026-11-16/results/finqa/submission.json \
  --output runs/external-pilot-2026-11-16/finqa-rescore.json
```

Initial implementation verification before the pilot: lint and **112 tests passed**.
Only a small development integration pilot is measured. The 100/100/150 coverage
targets, TAT-QA/ConvFinQA integration, full-agent FinanceBench corpus, calibrated
semantic judge, and human-reviewed final evaluation remain unfinished.
