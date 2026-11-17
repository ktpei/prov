# Shared-pool page ranking comparison

After independent review, commit the runner and this plan, generate a hash-bound
protocol, and commit that
protocol before any real query. Do not rewrite it to accommodate observed results.

## Fixed comparison

Use the same six exposed development cases, prepared inputs, native PDF corpus and
frozen location packets as `financebench-context-v1`, in prepared order. The separate
[validation reservation](../financebench-page-validation-v1/progress.md) remains
closed; its two prior-issuer exposures are disclosed, not replaced.

Use original questions and one declared document per case. Compute passage BM25
and physical-page BM25 once per case, retain up to 25 positive-score passages, then
derive two selected hit lists: baseline first five and equal reciprocal-rank fusion
with constant 60. All-page collection statistics, positive-page ranks, exact fraction
fusion and ties are implemented in `provenance/page_ranking.py`. No query rewriting,
new operands, page filtering or label-derived terms. Score all eligible passages and
physical pages; the 25 limit is a retention limit, not the scoring work count.

Both methods use identical, unchanged hit payloads and independent source/read
state. Read at most five exact parents per branch with `ranked-parent-once-v1`.
Compact returned-page metadata is fixed. Both context priorities apply to each
branch at one/three/five reads and the same 32,000 serialized-output-character cap.
No page text used only for ranking earns delivered-evidence credit. No extra reads,
continuations, replacements or alternative-evidence annotation changes.

Require numeric `PYTHONHASHSEED=0` before Python startup; check both the environment
and Python's disabled hash-randomization flag. Bind Python version/implementation,
parameters, runtime digest, dependency lock, driver, historical helpers, prepared
files, corpus identities, frozen packets, validation reservation/audit and previous
compact-run artifacts. Verify original and text hashes using Sources. Prior compact
control responses, read records/budgets, journals and projections must match exactly;
no normalization of those evidence fields is allowed. Case and protocol attribution
are checked independently.

## Execution and replay

Persist all six pending slots first. Persist each full shared ranking and both
selected hit lists before either branch reads. Keep separate durable read journals.
Save deterministic run state and journals under `deterministic/`; only
`receipt.json`, `telemetry.json` and that directory may exist at the run root.
The receipt binds their hashes. Timing records contain measured scoring and read
wall durations, outside the deterministic inventory. They are not claimed to replay
exactly; corpus construction and context projection are outside these timed regions.

Check historical control compatibility and frozen identities before marking the run
complete. Unexpected identity/mapping/inventory errors abort explicitly and preserve
all six slots. Ordinary bounded read failures retain their ranks and are not replaced.
Incomplete runs cannot produce a complete grade. No paid or provider calls occur.

Grading checks the receipt, replays the entire wrapper in a new temporary directory,
and requires byte-exact deterministic inventories across shared rankings, both
branches, all journals and both projection policies. Recheck identities and outputs
before opening packet JSON. Only then validate exact packet/source/case bindings and
grade. Keep grades outside the run inventory and recheck all inputs before writing.

## Measures and interpretation

Report all six cases, mapped denominators, shared scoring passes and full scoring
universe counts, derived search responses, read attempts/failures/truncation and
separate replay work. Per-case read budgets and context output sizes remain in the
saved run; timing stays separately bound. Equal caps do not imply equal measured cost.

Measure pool-25 parent opportunity using exact unions of candidate line ranges;
reject duplicate/wrong-source/invalid candidates. Never fill gaps with a bounding
range or mix incomplete alternatives. Report per-alternative role coverage and
actual candidate count. Empty pools and unmapped/unresolved packets cannot pass.
Pool opportunity does not imply that five reads deliver all required evidence.

Separately report selected-parent opportunity, returned search snippets, actual
returned reads and context-retained frozen-location coverage at 1/3/5. Pair retrieval
wins/losses/ties by exact case ID within each context policy; report blocks and all
six denominators. Failed reads have no delivered text. Parent opportunity is only a
potential window, never a read-success measure.

These are exposed-case development diagnostics, not semantic answer correctness,
exhaustive support judgments, human financial validation or generalization. Preserve
all original packets and their ambiguity notes, especially 3M's unresolved metric
convention and possible alternative evidence. Any later policy choice must precede
opening reserved validation content and requires its own prospective protocol.
