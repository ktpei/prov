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
