# H3 typed read authorization: first component

Implements the [frozen protocol](protocol.md) as `FactReadSession`, a controller
API that constructs its own existing FactReader from authenticated artifacts.
The controller supplies run ID and authorization binding source ID, exact original,
export and source-metadata hashes, reader version, and a fixed availability cutoff.
Model-facing integration is not enabled. No method accepts model-authored read
results, semantic acceptance flags or an override to the session cutoff.

Every accepted read records exact resolved arguments, actual returned response,
run/policy/source authorization identity and sequence in a content-bound receipt.
Blocked reads remain diagnostics. Completed deliveries bind their contributing
receipts and preserve the full payload, including nil, quarantine, context/unit,
continuations and original fragments. Return values and snapshots are copies.
Failed reconstruction does not mutate the session.

Chunk assembly verifies contiguous Unicode-character offsets, envelope identity,
per-chunk UTF-8 hashes, full length/hash and canonical JSON. The 256,000-character
limit bounds each payload and the sum of declared sizes of concurrently pending
reconstructions plus the current read. It does not bound total historical receipt
storage or the existing FactReader constructor's prebuilt payloads. Snapshots and
completed deliveries are backend audit data, not bounded model tool responses.
Shared dispatcher budgets and model-context projection remain required H3 work.

Replay constructs a fresh reader from separately trusted artifacts and authorization,
reexecutes every recorded request and compares the complete receipts/delivery/pending
inventory. The caller must independently persist and supply the snapshot digest;
a digest copied from the potentially altered snapshot is not an integrity anchor.
Run/cutoff rebinding and deleted trailing receipts reject against that anchor.

Independent design review required separating delivery from semantics and visibility,
controller-owned construction/cutoff, an externally anchored inventory, and explicit
aggregate reconstruction limits. Synthetic tests exercise the actual reader path,
Unicode chunks, complete/chunk equivalence, missing/overlapping ranges, hash/envelope
drift, source/cutoff authorization, immutable copies, quarantine/nil/zero, overflow,
and fresh-artifact replay. Independent implementation review passed all eight
focused tests. Shared-checkout lint and 523 tests passed, including thirteen
untracked tests owned by the paused assessment chat. Clean implementation commit
`eeb21b9` passes Ruff check/format, corpus validation and 510 tests. Existing
SQLite ResourceWarnings remain. The final aggregate test also completes the
first pending payload and verifies its reservation is released for the second.

This is not completed H3 or financial evidence admission. CalculationLedger stays
unchanged; no accepted H2 snapshot is emitted. Next: deterministic attribute/support
admission, submitted-request and final-synthesis visibility, answer-v2 claim and
derivation validation, shared dispatcher budgets, checkpoint compatibility and
full-agent integration. No source dataset, reserved task, paid inference or benchmark
quality score was used in this component's acceptance.
