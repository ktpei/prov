# Frozen research evaluation protocol

Registered before fresh inference, 2026-11-07. Runtime source baseline: `d9057ed`.
This task changes evaluation artifacts and documentation, not research behavior.

## Questions and run policy

- Six newly authored questions in `eval/company_fresh_tasks.json`, committed before
  inference. They use the existing four-document Cloudflare packet and are authored
  by a separate coding agent after runtime development. They are public development
  evaluation tasks, not an independent human-authored or contamination-proof holdout.
- Three numerical tasks, two single-source qualitative tasks, one missing-evidence
  task. Questions differ from the existing nine-task development set. Gold facts,
  evaluator queries, anchors, and rubrics never enter the research model's context.
- Attempt all six in ID order once. No prompt/retrieval/runtime changes, selective
  reruns, or answer-key fixes after seeing results. Preserve stopped/error outcomes.
- Existing 25-task excerpt benchmark: static validation only; no heldout inference
  or inspection of heldout outcomes. Existing nine-task packet benchmark: fresh
  offline retrieval diagnostic and historical-result audit, not a fresh model score.

## Model, limits, and spending

Use the exact selected model `deepseek/deepseek-v4.1-flash-1017` through the existing
OpenRouter/LangChain adapter. Temperature 0, 4,000 maximum output tokens, 10 model
calls, 12 tool calls, 180 seconds per task, 45-second request timeout. No web search,
OCR service, paid judge, or alternative model. Provider routing is unchanged.

Fresh experiment: **$0.15 aggregate**, **$0.05 per task** maximum application-side
reservations. Prior recorded development estimates total $0.3498927, so combined
estimated spending cannot exceed $0.4998927 under the previous $0.50 authorization.
No reply to an optional budget question increases that authorization. Stop for
uncertain accounting or aggregate exhaustion; never retry an interrupted paid run.
Tasks not attempted due to exhaustion must be reported separately from model errors.

Accounting uses the maximum currently advertised endpoint token rates, **$0.60
input / $2.40 output per million**, ignoring caching discounts. The public endpoint
snapshot is `preflight.json`. These higher conservative rates differ from cloud
development's $0.30/$1.20; compare estimated costs with that difference explicit.
Token reservations and reported usage are not provider invoice charges or a
guaranteed provider billing cap. Credentials remain in ignored local configuration.

## Scoring and reporting

Report completion, exact trace/quote validity, required numerical claim matches,
lexical citation-anchor coverage, and coding-agent semantic review separately.
Strict reviewed task success requires every requested finding, correct units,
period/basis/source, sufficient cited context, and no material unsupported addition.
Review narrative and structured claims, including claims with correct numbers.
Exact quotes alone do not prove entailment. Do not silently normalize or rewrite
the pre-grader after a format-related failure; explain it in the review.

Use all six pre-registered tasks as the end-to-end denominator, showing unattempted
tasks explicitly if budget stops the run. Also show any conditional attempted-task
rate with its denominator. Never combine historical best outcomes into a new score.
With six tasks and one company, a percentage is descriptive, not a broad financial
research accuracy estimate. Coding-agent reviews do not replace human finance review.
Fresh cross-source reasoning is not tested by these six tasks; the historical
cross-source audit remains a separate development result.

Record revision, source/task hashes, limits, complete public traces, costs, tokens,
latency, model/tool calls, tool errors, stop reasons, missing evidence, and per-task
reviews. Publish successes and failures together. Add a practical next-evaluation
plan based on the measured failure modes without tuning the scored runtime.
