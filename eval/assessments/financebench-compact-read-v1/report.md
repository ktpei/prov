# Compact PDF diagnostics result — 2026-11-16

Returned-page diagnostics eliminated all blocked projections on the six-case
cohort while preserving every search result, read window and evidence line. The
thirty compact read responses total 250,316 serialized output-string characters,
versus 1,045,305 for full metadata: a **76.05% reduction**. Complete evidence
coverage remains 0/6, 0/6 and 1/6 after one/three/five reads. This repairs the
measured context-size failure, not the five incomplete retrieved packets.

The following counts hold under both the unchanged production priority and the
unchanged earlier-read challenger:

| Measure | One read | Three reads | Five reads |
| --- | ---: | ---: | ---: |
| Full metadata: blocked projections | 4/6 | 5/6 | 5/6 |
| Compact metadata: blocked projections | 0/6 | 0/6 | 0/6 |
| Full metadata: complete retained packets | 0/6 | 0/6 | 1/6 |
| Compact metadata: complete retained packets | 0/6 | 0/6 | 1/6 |

Every evidence-completeness comparison has zero wins, zero losses and six ties,
both across metadata modes at fixed priority and across priorities within a mode.
Do not convert the operational improvement into an answer-accuracy claim or a
priority-policy preference. Costco remains the sole complete five-read packet.
Zero blocks also does not mean every read survives: at five reads, newest-first
retains three reads per case; earlier-first retains three except for 3M, which
retains two.

## Size and provenance

Per-read output cost falls from 19,624–50,152 to 4,137–13,002 serialized-output
characters. These costs count each actual read response once, excluding searches
and replay, not repeated prefix histories, prompt tokens or source-file bytes.
Search responses add an unchanged 32,850 characters per mode. The [receipt](receipt.json) records
per-case sizes, retained ranks, blocked statuses, both modes' raw-file hashes and
the exact reduction calculation. [Result](result.json) records coverage, blocking,
paired outcomes, mode attribution and operation counts.

The compact response retains full diagnostic entries only for physical pages in
the actually returned lines. All other extraction fields—including global warnings,
empty-page lists, document page counts, uncertainty, package versions and OCR
status—remain identical. Each projection identifies the full original diagnostics
by canonical hash and manifest reference. Corpus originals, native text and full
metadata are unchanged. Every non-extraction response field matches full mode.

## Frozen execution and compatibility

Implementation and safeguards were committed in `8ca3be7`; both protocols were
frozen in `8ea5896` before any cohort call. Outer protocol SHA-256:
`9a3651ff6d292f9dbc9b58e7a5c6d5a08815e2eefee05ec5960bc18cca1aeb37`.
The outer protocol binds 32 files, the new runtime and explicit mode assignments.
Its shared inner protocol does not itself encode the metadata mode.

Current-runtime full mode exactly reproduces the historical searches, reads,
budgets, journals and both policy snapshots. Only the validated top-level protocol
hash changes in the normalized run comparison. Its grade also matches after only
the validated protocol/run-hash substitutions. Compact searches were checked
against those verified full responses before reads dispatched. The metadata-only
contract was then checked before grading.

Both original mode runs completed before labels were parsed for grading. Each
mode's grade performed its own exact replay before its packet parsing. Both grades
ran in one process: the second replay therefore occurs after first-grade labels
have been seen. This is per-condition data-flow isolation, not process-wide label
secrecy. Labels do not control retrieval, reads, metadata projection or retention.

Each mode used six collection searches and thirty reads, then six searches and
thirty reads for verification. Total: twelve collection searches/sixty reads plus
twelve verification searches/sixty reads. No failed or truncated reads, retries,
model/provider calls, extra source windows or holdout runs occurred.

Completed commands, using safe-path Python invocation:

```sh
PYTHONPATH=. uv run python -P eval/assessments/financebench-compact-read-v1/assess.py run \
  --protocol eval/assessments/financebench-compact-read-v1/protocol.json \
  --run-dir runs/financebench-compact-read-v1
PYTHONPATH=. uv run python -P eval/assessments/financebench-compact-read-v1/assess.py grade \
  --protocol eval/assessments/financebench-compact-read-v1/protocol.json \
  --run-dir runs/financebench-compact-read-v1 \
  --output-dir runs/financebench-compact-read-v1-grade
```

An [independent audit](audit.json) verified all 32 bound files, mode inventories,
historical compatibility, every metadata projection and all counts without new
retrieval, projection or grading calls. Outputs are preserved and not overwritten. Historical protocols/results remain
bound to their original runtime and were not edited to admit the new implementation.

## Remaining limits

This reuses exposed development cases and is not fresh validation. The original
3M, Coca-Cola and Verizon semantic caveats remain unresolved; source-location
mapping is not financial adjudication. Global warning metadata intentionally
remains complete, so compact mode is not a universal response-size guarantee.

The compact format remains opt-in; production defaults and priority policies are
unchanged. The next work is operational integration of the explicit mode and
source-aware retrieval that supplies the missing required components. Neither
full-agent benchmark inference nor a financial-accuracy claim follows from this
result. All 342 tests and lint pass. Spending remains $0.4814193.
