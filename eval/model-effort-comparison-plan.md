# Model and reasoning-effort comparison preparation

2026-11-16 · proposed, not executed or frozen for inference

The user explicitly authorized choosing and comparing different models and effort
levels. Prior pilots used `deepseek/deepseek-v4.1-flash-1017` with effort omitted;
do not relabel those historical requests with today's provider default. H1/H2
synthetic tests are not model-quality trials. Existing spending authorization is
unchanged: reconcile the $1 aggregate limit, recorded $0.4814193, pending/uncertain
attempts and current account usage before spending any nominal remainder.

## Initial comparison candidate

A read-only Astra review checked current public catalog/endpoint documentation.
It proposes exact DeepSeek baseline low/high versus `openai/gpt-6-luna` low/high
for a small supplied-context, tool-free comparison. This isolates model/effort
without confounding unfinished H2/H3 tools. Gemini Flash is a later candidate,
not an additional initial arm. Reverify capability/pricing metadata and pin the
actual endpoint before adopting any candidate; a source listing is not a successful
compatibility test. Never silently substitute an unavailable exact model ID.

Sources: [OpenRouter catalog](https://openrouter.ai/api/v1/models),
[DeepSeek](https://openrouter.ai/deepseek/deepseek-v4.1-flash-1017),
[Luna](https://openrouter.ai/openai/gpt-6-luna),
[Luna API capabilities](https://developers.openai.com/api/docs/models/gpt-6-luna),
[provider routing](https://openrouter.ai/docs/guides/routing/provider-selection).
The review found Luna low/high tool use requires a different transport than the
current Chat Completions tool path; do not infer tool-free compatibility proves
full-agent compatibility. Reasoning/signature preservation is another full-agent
adapter gate.

Candidate pilot: four already authorized development tasks × four arms, one
attempt each, no retry/repair. Proposed maximum $0.40 aggregate, $0.10/arm and
$0.025/task, subject to reconciliation and conservative input/output reservation.
These are proposed caps, not clearance to spend. Select tasks by frozen metadata
rules from already exposed development groups, excluding all reservations and
unresolved identities; do not select previous successes. Existing six-issuer
development inputs are a candidate pool, not a new unseen-source claim.

Hold input/prompt/output contract, harness revision, attempts, timeout and common
completion ceiling fixed; interleave arms. Freeze a feasible token ceiling before
observing results. Effort labels are only comparable within model; common ceilings
do not imply equal compute or equal dollars. Report actual cost and reasoning-token
breakdown. A separate equal-dollar study would answer a different question and
requires its own allocation. Four tasks provide diagnosis, not a leaderboard.

## Implementation gates before paid dispatch

1. Explicit effort and endpoint routing configuration, retaining omitted-effort
   legacy behavior. Model-specific temperature policy; reject unsupported settings
   before dispatch. Capability claims come from pinned metadata plus offline tests.
2. Include effective effort, routing/fallback controls, completion limit and rates
   in receipts/checkpoint identity and runner ledgers. Do not change historical runs.
3. Preserve request/provider/model IDs, usage details, reasoning/cache tokens,
   finish reason and reported cost. Reasoning is part of total output: never bill
   it twice. Distinguish reservation, rate estimate and provider-reported settlement.
   Missing billing metadata cannot become zero cost. See
   [reasoning accounting](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)
   and [usage fields](https://openrouter.ai/docs/cookbook/administration/usage-accounting).
4. One aggregate ledger prevents four arm directories from each spending the same
   remainder. Retain pending/skipped/truncated/failed attempts; uncertain billing
   stops dispatch. Include any live compatibility canary in the same total cap.
5. Offline request/usage tests, legacy regression checks, required lint/tests,
   clean runtime, then a committed task/capability/scoring protocol. Reconcile
   account/ledger usage immediately before inference.

Measure paired numeric and semantic outcomes, supportedness, abstention, invalid
output, truncation, completion, latency, usage and actual cost. Keep mechanical
checks separate from independently reviewed semantic support. No model winner
or effectiveness improvement is established by this preparation.

Answerability is judged from the supplied packet independently of model output.
Separate full/partial/abstained disposition from individual claim support. A
caveated numerical assertion still needs evidence; a supported partial answer
with an explicit unresolved calculation is not equivalent to an unsupported guess.
Report substantive-answer coverage, supported success over assigned tasks,
unsupported substantive answers, appropriate and unnecessary abstentions, and
scoring coverage. Retain invalid judgments and runtime/budget failures. Do not tune
coverage thresholds after observing results or infer non-disclosure from a retrieval
miss. This reporting clarification adds no judge framework or inference calls.
Follow the existing benchmark plan's blinded review: assign anonymous output IDs
and grade each raw answer against fixed evidence/rubrics before revealing model,
effort, latency or cost. Retain a separate stable arm mapping; do not rewrite
answers to equal length or treat preference judgments as financial validation.
