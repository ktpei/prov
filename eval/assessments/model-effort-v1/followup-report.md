# Follow-up result: HTTP 404, no completed answers

The one deliberate follow-up frozen at `2109681` ran from a clean checkout.
Its first request (Costco, DeepSeek low) returned
`Comparison transport failed: API HTTP 404; no automatic retry`.
The safe diagnostic change preserved the status in the durable ledger. No output,
generation ID or usage was returned. The runner stopped all remaining calls;
there was no provider fallback, configuration change or automatic retry.

Sixteen rows remain recorded: one attempted/failed and fifteen unvisited. Of
the unvisited rows, four belong to the frozen 3M exclusion and eleven are eligible
requests. Zero outputs means zero semantic review coverage, not zero financial
accuracy. Across both pilots, there are two actual attempts, both on the same
task/arm, and no usable model comparison. The first run's unknown failure cause
must not be retroactively relabeled HTTP 404.

Each attempt retains its full $0.0132189 uncertain reservation. Total uncertain
accounting is $0.0264378; with $0.4814193 historical conservative spend, total
authorization accounting is $0.5078571, leaving $0.4921429 against $1. These are
conservative reservations/estimates, not invoice amounts. No claim of zero cost
follows from the HTTP status. Paid comparison work is stopped for this cycle.

## Read-only investigation

The public endpoint metadata still lists the exact DeepSeek model, provider tag,
reasoning/max_tokens parameters and pricing consistent with the frozen request.
The OpenAI model/provider also remains listed, but no OpenAI arm was dispatched.
Selected metadata, raw snapshot hashes and run hashes are retained in
[followup-result.json](followup-result.json). Public catalog presence is not
account-specific routability or successful inference compatibility.

OpenRouter documents provider-only routing and parameter-based filtering in its
[routing guide](https://openrouter.ai/docs/guides/routing/provider-selection),
and distinct request/generation failures in its
[error guide](https://openrouter.ai/docs/api/reference/errors-and-debugging).
Neither identifies this request's cause from a bare 404. No response body was
retained, and no unsupported inference about account settings, model removal,
provider health, or pricing eligibility is warranted. Further diagnosis must
use read-only account/routing evidence or offline fixtures before a new protocol;
do not keep repeating inference requests to guess at settings.

Independent review approved the follow-up's conservative budget treatment and
required explicit acknowledgement of the deliberate repeat and unresolved charge.
The clean checkout passed all 19 adapter/runner tests before dispatch; the prior
implementation passed shared-checkout lint and 515 tests. This cycle establishes
diagnostic preservation and an observed live failure, not improved finance QA.
