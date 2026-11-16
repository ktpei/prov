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

No real cohort search, candidate scoring, read or grade has occurred. The protocol
must be generated and committed after this implementation commit. The six earlier
exposed development cases remain the comparison cohort; all separately reserved
validation documents/questions remain closed. No paid/provider calls are involved.
