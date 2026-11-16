# Page-ranking assessment status — 2026-11-16

The [runner](assess.py) implements the [reviewed interface design](../../page-ranking-assessment-design.md)
and [execution plan](plan.md). Independent implementation and grading reviews pass.
All 369 repository tests and lint pass, including eleven new assessment tests.
Review found and fixed an in-memory replay-object/file mismatch path; labels now
remain closed until the returned replay object matches its exact written artifact.
Telemetry is also object-bound before hashing and separated from deterministic replay.

Synthetic checks cover shared ranking count, full collection/replay/grading,
candidate tampering even with a rehashed receipt, replay-object-only corruption,
extra files, telemetry mutation, interruption with all-six slots preserved,
startup hash seed, exact disjoint pool unions, alternative isolation, all-read
failures, challenger-only failures and truncated boundary evidence. Successful
packet parsing is checked to occur only after both branches finish replay.

The protocol was committed at `07b10e0` before execution. The real comparison and
whole-wrapper replay/grade are complete: [report](report.md), [result](result.json).
Both policies retain 1/6 control versus 0/6 challenger at five reads (one Costco
loss, no wins); shared pool-25 opportunity is 2/6. No failures, truncation or context
blocks occurred. The challenger is not promoted. No paid/provider calls were made.
All separately reserved validation documents/questions remain closed.

Independent [saved-artifact audit](audit.json) verifies all 35 bindings, original
receipt/journals, historical control compatibility, shared response identity and
reported counts/character arithmetic. It did not rerun the recorded replay.

A [post-hoc saved-pool diagnosis](pool-diagnosis.md) finds exact parent-window
witnesses of one window for Costco and two for American Water Works. The other
four pools lack required frozen locations; none merely requires more than five
windows. These label-assisted witnesses are evaluator-only and do not change scores.
