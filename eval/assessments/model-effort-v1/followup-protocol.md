# Model/effort diagnostic: one deliberate follow-up

Freeze before dispatch. Runtime `6875c1b` changes only safe transport diagnostics
relative to the first pilot. All task selection, original inputs, rubric,
reference exclusions, model/provider/effort configurations, ordering, output and
time limits, and evaluation rules from [pilot-protocol.md](pilot-protocol.md)
remain fixed. Verify [pilot-bindings.json](pilot-bindings.json) before execution.
The reviewed bundle and arm bytes are reused without editing. No new selection,
source research, or heldout content is required.

The first run remains terminal and immutable. This is a separate, explicitly
recorded follow-up to obtain either completed outputs or a safe failure category;
it is not an automatic retry or a resume of the original ledger. Do not combine
the two runs into a success-only sample. Record the first failed attempt alongside
the follow-up when reporting feasibility and cost.

The first request's $0.0132189 billing uncertainty remains unresolved. Treat that
entire reservation as spent for authorization purposes; do not release it based
on unchanged aggregate key usage. Combined prior conservative accounting is
$0.4946382, leaving $0.5053618 under the existing $1 authorization. This follow-up
is capped at $0.40 total, $0.10 per arm and $0.025 per attempt, so even its full
cap plus the prior uncertain reservation remains below authorization. Recheck
the key's available limit before dispatch; this is capacity checking, not proof
of request-level billing settlement.

This conservative budget review deliberately supersedes the first report's
settlement-before-next-trial gate for this one follow-up only. It does not claim
that billing was reconciled. Independent review confirms the full retained
reservation plus the new cap fits the authorization. The first task/arm request
may be repeated; report it candidly as a deliberate second attempt, not a first
attempt merely because it has a new output directory.

Run once from a clean checkout containing this freeze, with output directory
`runs/model-effort-v1/followup-results`. No reuse, no retries, no fallback. Stop
on uncertain billing or integrity failure exactly as the runner specifies. If
transport fails again, preserve the category and stop live comparison work;
investigate using read-only metadata and offline fixtures before considering any
further separately reviewed protocol. Do not silently adjust routing or settings.

There are sixteen selected rows: twelve eligible requests and four predeclared
reference exclusions. An early stop may label unvisited exclusions as skipped;
report their frozen reference disposition separately. Blinded review is possible
only for completed outputs. This tiny exposed sample cannot establish model
superiority, production promotion or full-agent financial correctness.
