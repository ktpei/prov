# Compact-read assessment status

The opt-in returned-page projection is implemented in `e675939`; full metadata
remains the default. This wrapper reuses the historical six-case collector,
projectors and grader under a new runtime without changing the historical files.
The new outer protocol will explicitly attribute full and compact metadata modes;
a shared inner protocol alone does not encode that choice.

Eight synthetic tests pass, including default-compatibility gating, compact search
mismatch before read dispatch, exact evidence preservation, constructor restoration,
run/grade output replacement, typed metadata identity and final inventory checks.
Independent review found immediate file/object binding and Boolean/integer comparison
gaps; regression tests cover the fixes, and re-review accepted the wrapper with
no remaining blockers. All 342 repository tests and lint pass.

[Frozen execution](report.md) is complete: current full mode exactly reproduces
historical outcomes, and compact mode eliminates all blocked projections under
both priority policies. Read-response characters fall 76.05%; complete coverage
remains 0/6, 0/6 and 1/6. The metadata-only contract and both replays pass. The six selected cases,
existing annotations, both priority policies and 32K character budget stay fixed.
This is development diagnostics, not a fresh or financially adjudicated benchmark.
