# Model/effort comparison infrastructure acceptance

2026-11-16 · implementation `01983f4` · offline acceptance

The [frozen infrastructure protocol](infrastructure-protocol.md) is implemented as
a tool-free direct JSON adapter plus one durable interleaved comparison runner.
Legacy full-agent/benchmark paths remain unchanged. This shared comparison path
is not an exact historical adapter replication or a full-agent model comparison.

Each arm binds explicit effort, optional temperature, capability identity, routing
and reservation rates. Receipts retain the dispatched application JSON without
credentials. The adapter validates actual provider/model identity, preserves
usage and response IDs, settles reported cost once, and retains billed failures.
Reasoning counts remain within completion usage. Unknown billing and integrity
errors stop the entire comparison; no automatic retry/resume exists.

The runner persists every selected task×arm row before dispatch, rotates arm
order, applies per-attempt/arm/aggregate caps, and retains failed/skipped attempts
in per-arm scoring. Known billing and raw outputs persist before parsing; scorer
dependencies are checked before requests. Its CLI requires explicit live mode,
prepared inputs, arm configuration, output path and all spending caps.

Independent Astra review reproduced and helped fix malformed token-detail handling,
usage above declared ceilings, loss of full response metadata on cost overrun,
loss of known billing on parser failure, and late TAT-QA dependency checking.
All seventeen adapter/runner test groups pass. Shared-checkout `yarn lint` and
513 tests pass; clean commit `01983f4` passes the same lint/validation checks and
500 tests. Thirteen unrelated untracked XBRL tests are excluded from clean counts.
Existing SQLite ResourceWarnings remain. No paid requests occurred during testing.

The [spend preflight](spend-preflight.json) independently reconciles thirteen
historical ledgers to $0.4814193, with 66 accounted entries and no pending or
uncertain local charges. A read-only key query reports $0.113681698 aggregate
provider usage and $0.988928912 remaining under the $1 daily key budget at its
recorded timestamp. Preserve conservative historical accounting; do not add that
aggregate provider usage again as a second charge. This is not an invoice audit
or whole-account credit-balance claim. Repeat the key check immediately before
the bounded paid experiment.

Accept infrastructure only. A live task/rubric/capability/cap protocol must be
committed before paid dispatch. No model winner or financial-effectiveness gain
is established. Provider capabilities are documentation/metadata evidence until
a live request demonstrates compatibility; any failure remains in the pilot.
