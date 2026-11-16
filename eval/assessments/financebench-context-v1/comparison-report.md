# Six-case context comparison — 2026-11-16

The fixed earlier-read challenger did not improve coverage on this cohort. Both
policies retain complete annotated evidence for 0/6, 0/6 and 1/6 cases after
one/three/five reads. Five of six five-read projections are blocked because their
required latest results and omission notices cannot fit the existing budget.
This is a context-availability result, not financial answer accuracy.

| Evidence channel | One read/hit | Three | Five |
| --- | ---: | ---: | ---: |
| Selected parent-passage opportunity | 0/6 | 0/6 | 1/6 |
| Returned search snippets | 0/6 | 0/6 | 0/6 |
| Delivered reads | 0/6 | 0/6 | 1/6 |
| Baseline retained reads | 0/6 | 0/6 | 1/6 |
| Earlier-read retained reads | 0/6 | 0/6 | 1/6 |
| Blocked projections, each policy | 4/6 | 5/6 | 5/6 |

All cutoffs have zero paired wins, zero losses and six ties. These ties include
operationally blocked projections; they do not establish equivalence of the two
retention strategies. Costco is the only complete five-read packet. At five reads
both policies retain only Costco's fifth result; all other cases are blocked.
Retrieval itself delivers incomplete packets for five cases, so eliminating
context blocking alone is not demonstrated to repair those evidence gaps.

## Frozen inputs and execution

Annotation packets were independently reviewed and committed in `ddb8bd6` before
retrieval. The runner/plan were independently reviewed and committed in `bce0afb`;
[exact protocol](comparison-protocol.json) was committed in `289cdd0` before the
first search. Protocol SHA-256 is
`9c65970ae428b9b11205801a43817b2da610b799562fef819f9cbcf620e7240d`.
The protocol binds twenty files plus the runtime and uses unchanged production
and earlier-read projectors under 32,000 serialized output-string characters.

All six cases completed: six original searches, thirty original reads, zero failed
or truncated reads. Grading independently repeated six searches and thirty reads,
then required byte-exact run, snapshot and journal equality before packet parsing.
All source/input identities and inventory were rechecked. An [independent audit](comparison-audit.json)
confirmed exact case order, source/result/journal hashes and all reported counts
without issuing new search/read calls. No paid/provider calls,
query substitutions, expanded reads, source replacements or holdout runs occurred.

The first direct-script launch failed during imports: adjacent `select.py` shadowed
Python's standard `select` module. It created no run output and executed no search
or read. The safe-path invocation below ran the unchanged frozen program. This
startup correction is preserved in the result record and was not a retrieval retry.

```sh
PYTHONPATH=. uv run python -P eval/assessments/financebench-context-v1/compare.py run \
  --protocol eval/assessments/financebench-context-v1/comparison-protocol.json \
  --run-dir runs/financebench-context-v1-comparison
PYTHONPATH=. uv run python -P eval/assessments/financebench-context-v1/compare.py grade \
  --protocol eval/assessments/financebench-context-v1/comparison-protocol.json \
  --run-dir runs/financebench-context-v1-comparison \
  --output runs/financebench-context-v1-comparison-grade.json
```

These commands document the completed run; existing outputs are not overwritten.
[Result summary](comparison-result.json) binds raw run/grade/journal hashes and
records every case's retained ranks, budget sizes, blocked statuses and evidence
completeness. Raw artifacts remain under `runs/`.

## Interpretation and next investigation

The earlier 2/3-versus-0/3 improvement on exposed cases did not reproduce here.
Do not promote the challenger from this evidence. The source-quality pipeline must
address both incomplete retrieved evidence and oversized required tool responses.
Initial inspection of saved responses shows that each read repeats document-wide
extraction diagnostics, including per-page details. Diagnose those sizes using
saved responses before defining a separately frozen remedy; do not alter this
result, its packets or its policies.

All six packets map source locations, but the [annotation caveats](annotation-report.md)
remain: 3M's M&A/organic-growth distinction, Coca-Cola's net-income convention and
Verizon's classification assumption are unresolved. This fixed synthetic history
experiment neither chooses agent search actions nor measures model/human financial
accuracy. Public-development exposure and unresolved cross-suite issuer identities
remain limitations. Native extraction outside the ten reviewed pages remains
financially unverified.

All 329 tests and lint pass. Production policies, existing benchmark answers and
the original 25-task corpus/15-task holdout are unchanged. Spending remains
$0.4814193.
