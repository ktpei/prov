# Opt-in raw table runtime

The standalone `TableSources` composes frozen-source validation with native HTML
sidecars. It exposes `search_tables` and `read_table` without
changing the existing research graph, model instructions, line citations, or
checkpoint behavior. Runtime code never loads evaluator fixtures.

Search is scoped to a declared source and returns at most five deterministic
lexical table hits and literal matched-row candidates. It assigns no financial
roles and does not make snippets citable evidence. Read takes a table ID and at
most eight distinct row indices. The generic `table-window-v1` policy includes
first five physical rows plus requested rows and their immediate predecessors.
It preserves exact nonempty, nonhidden cells and their geometry, all period
columns, and split signs. Empty omissions are explicit and never mean zero.

The entire compact canonical JSON response (sorted keys, no separator spaces,
Unicode retained, nonfinite numbers forbidden) is capped at 12,000 characters. Oversize reads
fail atomically rather than dropping headers or values. Original hashes, sidecar
version/hash, source-manifest hash, request/window indices, and unresolved semantic
status identify each result. Private cache state must not be mutable through
returned objects. Unsupported originals fail explicitly; no network access exists.

The [fixed offline protocol](reports/table-runtime-2026-11-16/protocol.json)
separates explicit-window controls from question-only search followed by one read.
Evaluator labels assess required-cell presence only after the call. They never
choose runtime columns, rewrite search queries, or populate typed answer fields.
Raw tool coverage, inferred association correctness, and financial answer
correctness are distinct; the latter two remain unmeasured in this slice.

## Later graph and citation integration

Original HTML line numbers are not legacy extracted-text `L` locators. Do not
convert them or mark lines read based on a table read. Repeated strings cannot
establish a safe cell-to-line mapping. Normalized cell text is not an original
HTML-byte quotation.

A later explicit runtime profile can add cell locators such as `C:table-8-r31-c2`,
with separate `seen_cells` state. Validation must check source/original/sidecar
identity, successful read membership, nonhidden status, and exact normalized
quote fidelity. That proves provenance, not financial meaning. Split signs and
headers need their own cell citations.

That profile must version and bind actual instructions/tools, table hashes,
checkpoint identity and state, context-retention rules, repair/finalization
messages, replay reconstruction, and table-aware evaluation. Keep legacy line
locators and replay unchanged. Adding table dispatch alone is insufficient because
the current graph assumes `search` and `read_source` throughout these interfaces.

This architecture was independently reviewed by a coding agent. Existing frozen
pilot scores and the untouched original holdout remain regression boundaries.

## Reproduce the fixed offline probe

```sh
uv run python -m eval.scripts.table_runtime_probe \
  --protocol eval/reports/table-runtime-2026-11-16/protocol.json \
  --fixtures eval/table-evidence-fixtures.json \
  --corpus data/cloudflare-2024-q3 \
  --output runs/table-runtime-2026-11-16
```

Use a new output directory. The probe retains actual calls/responses, identities,
response sizes, latency, and errors for every selected case. Its raw-context grader
checks the trusted manifest hash, sidecar hash, exact cells and captions, and
rejects error-bearing responses. It does not synthesize role labels or typed
answers from the fixture to make a read pass.

Table search v2 leaves table scores and order unchanged, but excludes the first
five physical rows from read candidates because every read already includes that
prefix. V1 remains selectable for baseline replay. Protocols without an explicit
search version replay v1; challenger protocols specify v2. The first-three row
selection rule is unchanged, and no fixture roles or answer values enter ranking.

## Separate locked-assessment execution

`eval.scripts.table_assessment_run` is a distinct search-only runner for future
locked assessments. It accepts strict questions containing only `id`, `source_id`
and `question`, plus a protocol binding question bytes, corpus manifest, runtime
code/dependency digest and explicit search version. It never opens annotations or
runs oracle reads. The existing four-case probe remains unchanged for replay.

```sh
uv run python -m eval.scripts.table_assessment_run --runtime-digest
uv run python -m eval.scripts.table_assessment_run \
  --protocol RUN_PROTOCOL.json --questions QUESTIONS.json \
  --corpus CORPUS_DIRECTORY --output NEW_RUN_DIRECTORY
```

The protocol version is `table-assessment-run-protocol-v1`; its only other fields
are `questions_sha256`, `corpus_manifest_sha256`, `runtime_sha256` and
`search_version`. Question files use `table-assessment-questions-v1` and a `cases`
list. Extra fields are rejected before retrieval. Runtime hashing includes all
Python files under `provenance`, scripts under `eval/scripts`, `pyproject.toml`
and `uv.lock`, including untracked matching files. This is an identity check,
not an enforced gold-confidentiality boundary or a complete assessment gate.

All cases are persisted before execution. A running-case receipt precedes dispatch;
completed search/read responses are persisted before the next call. Interruptions
retain observed traces and pending cases. No-hit, search errors and read errors
remain outcomes; constructor/integrity failures invalidate the run. Final checks
revalidate input bytes, runtime digest and corpus original/text hashes. Output
directories cannot be reused. Hard process termination may leave an explicitly
incomplete running receipt; it must not be reported as a completed run.

The runner is tested only with invented HTML. Separate annotation grading is now available below. It does not yet provide
the complete staged
provenance gates in the [broader assessment plan](assessments/native-html-v1/plan.md).
No new real-document accuracy result is claimed.

## Precommitted annotations and separate grading

New locked assessments use `table-assessment-run-protocol-v2`. It adds the sole
field `assessment_receipt_sha256` to v1. The runner copies this opaque digest into
its report but never opens a receipt or annotation file. V1 execution remains
supported for compatibility; the new grader requires v2.

Before execution, freeze a `table-assessment-receipt-v1` JSON object containing
`version`, `questions_sha256`, `annotations_sha256`, `corpus_manifest_sha256` and
`runtime_sha256`. Commit that receipt and its referenced artifacts according to
the assessment gates, then bind its exact byte hash in the run protocol. After
execution, freeze a grading protocol with version `table-assessment-grade-protocol-v1`
and the exact hashes of `run_protocol`, `questions`, `report`, `annotations` and
`receipt` (each field suffixed `_sha256`). This avoids circular identities.

```sh
uv run python -m provenance.table_assessment \
  --protocol GRADE_PROTOCOL.json --run-protocol RUN_PROTOCOL.json \
  --questions QUESTIONS.json --report FROZEN_RUN_REPORT.json \
  --annotations ANNOTATIONS.json --receipt ASSESSMENT_RECEIPT.json \
  --corpus CORPUS_DIRECTORY --output NEW_GRADE_DIRECTORY
```

The grader validates completed status, exact case order and fixed denominators,
then replays the prescribed source-scoped search and at most one read. It checks
arguments, response bytes/hashes/sizes, call counts and statuses against that
replay before opening annotation bytes. Duplicate JSON keys and nonfinite JSON
constants are rejected; canonical comparison distinguishes booleans and numbers.
It rechecks local inputs, corpus and runtime before publishing a grade and refuses
output reuse. Invalid inputs raise an error and produce no successful grade.

Annotations use `table-assessment-annotations-v1`, with question/manifest hashes,
source bindings (`original_sha256`, `sidecar_version`, `sidecar_sha256`) and one
ordered case per question. Each case has `id`, `source_id`, `disposition`,
`required_components`, `alternatives` and `reason`. Dispositions are `mapped`,
`unmapped` or `unresolved`. The required-component list must be nonempty and unique.
Every mapped alternative contains one `table_id` and a `components` object mapping
**every** declared role to nonempty visible cell-ID lists. Missing roles, empty or
hidden cells and duplicate alternatives are rejected. Unmapped/unresolved cases
require a reason and no partial alternatives; they cannot pass.

Complete context requires a single complete evidence alternative in one actual
read. Components are never pooled across alternatives or tables. Reports preserve
all selected cases, show mapped eligibility and disposition counts separately,
and report table hits at 1/3/5 plus per-alternative component coverage. Numeric
answer correctness, inferred associations and annotation adequacy remain unmeasured.

The receipt establishes consistent identities across artifacts; it does not prove
historical timing without the external committed gate chain. Replay establishes
reproducible behavior, not cryptographic proof that a historical run occurred.
Neither proves that annotators listed every necessary qualification. These
limitations must accompany new assessment results. Current verification uses
invented HTML only; two of six issuer copies passed acquisition and extraction,
but the cohort remains incomplete and ungraded.


## Temporal control protocol

Protocol v3 and question schema v2 add explicit `as_of` values and conservative
source-availability bounds. Annotation schema v2 keeps availability controls
separate from positive financial evidence. The [availability policy](source-availability-policy.md)
defines schema, uncertainty, trace requirements, metadata provenance and SEC
calendar-day conventions. No real temporal assessment has run yet.


## Explicit sidecar version protocol

`table-assessment-run-protocol-v4` retains v3's temporal questions and annotation
schema v2 and requires `sidecar_version`, exactly `native-html-tables-v2` or
`native-html-tables-v3`. It records that value in the run report. The tool snapshot,
replay verifier and annotation geometry extractor all use the declared version;
report or annotation version/hash mismatches reject grading. The receipt and
frozen protocol hashes bind the selected geometry. Versions v1–v3 continue to
imply sidecar v2 and reject an explicit override; their report shapes stay unchanged.

`TableSources(..., sidecar_version="native-html-tables-v3")` enables template
isolation for standalone tools. Its default remains v2 for exact replay. Table and
cell IDs belong to one sidecar version: removing an inert template table can
renumber later visible tables, so annotations must be rebuilt and committed for
the chosen geometry rather than relabeled.

Synthetic integration covers a template decoy followed by a visible table,
receipt-bound grading, mismatched report/annotation identities, invalid/missing
versions, historical override rejection and blocked controls without retrieval
construction. Thirty-six historical search/read responses replay exactly across
all three search versions. [Evidence](reports/table-template-2026-11-16/runtime-compatibility.json).
No new real financial assessment or promotion has occurred. Any use in the
six-filing assessment requires a separately committed runtime/protocol amendment;
existing gates remain unchanged and cannot validate the newly changed code.
