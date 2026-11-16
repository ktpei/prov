# External finance benchmark workflow

Implemented development foundation, 2026-11-16. This adds pinned acquisition,
five dataset adapters, development selection, input/reference separation, and
offline scoring. A separate explicit tool-free runner supports OpenRouter;
its implementation tests do not establish financial model accuracy. Existing benchmarks, heldout tasks, and
historical grades are unchanged.

## Acquire and prepare

The checked-in [catalog](external-sources.json) records immutable upstream
revisions, byte hashes, and terms. Raw third-party data and gold artifacts stay
under ignored `runs/`; do not commit or index these files into agent retrieval.
FinEval and FinanceBench are for noncommercial research under their stated terms.
See [verified research](external-benchmark-research.md) for underlying rights and
code/data license distinctions.

```sh
uv run python -m provenance.benchmark_data \
  --name finqa-dev --output runs/benchmark-data/finqa-dev
uv run python -m provenance.benchmarks prepare \
  --source-manifest runs/benchmark-data/finqa-dev/source.json \
  --input runs/benchmark-data/finqa-dev/finqa-dev.json \
  --condition supplied_context --count 100 --seed 20261116 \
  --output runs/benchmark-prepared/finqa-dev
```

Acquisition verifies the exact downloaded bytes before creating the output.
Both commands require new output directories and never replace an earlier run.
The catalog also provides `fineval-cfa-easy`, `fineval-cfa-challenge`, and
`financebench-public`, `tatqa-dev`, and `convfinqa-dev`. ConvFinQA acquisition
verifies both archive and selected JSON member hashes without extracting arbitrary
ZIP members. CFA files are Parquet: use `uv run --with pyarrow python`
for their preparation (optional import dependency, not required for the harness).

Supported conditions:

| Dataset | Conditions | Permitted input |
| --- | --- | --- |
| FinEval | `model_only` | Query, including its options |
| FinQA | `supplied_context` | Question, pre/post text, table |
| TAT-QA | `supplied_context` | Question, whole table and paragraphs, no relevance labels |
| ConvFinQA | `reference_history`, `agent_history` | Current turn and permitted prior answers only; conversation execution pending |
| FinanceBench | `evidence_supplied` | Question and gold evidence passages, explicitly diagnostic |
| FinanceBench | `full_agent` | Question and document name; document acquisition/runtime integration still required |

Preparation emits `manifest.json`, `tasks.json`, and `inputs.json`. Only
`inputs.json` may reach the model. `tasks.json` contains private evaluator
references, including programs and answer evidence. Allowlist projection excludes
all other annotations and precomputed retrieval. Hashes identify each projection.
The separate files are an application boundary, not an operating-system sandbox;
a runner must not grant its agent filesystem access to the evaluator directory.

Selection uses a declared seed and stable hashes. New preparation uses partition
v2: FinQA `TICKER/YEAR` reports (rather than individual pages) and FinanceBench
document names stay in one internal partition; 20% of hash buckets
are reserved for `internal_final`, and only `dev` tasks are emitted. This is a
public-data development partition, not a secret holdout. Legacy v1 manifests grouped FinQA pages and still replay unchanged. V2 uses report
groups for released page-path filenames. The development-exposure registry keeps
previously reviewed reports in development, including overlapping ConvFinQA contexts. CFA shared
scenarios and cross-suite FinQA/ConvFinQA overlap require additional auditing.
The six content-bound unresolved issues in `eval/reference-issues.json` are applied
to new preparations only. Source/task hash mismatches fail; gold is never rewritten
or excluded. Review-required tasks stay in the denominator with null accuracy and
are skipped before any paid request. Existing frozen manifests are unchanged.
Changing the seed changes the partition and is not a legitimate way to replenish
a final set already inspected or tuned on. Original upstream split labels remain.

## Score saved predictions

The JSON prediction envelope must identify the exact prepared manifest:

```json
{
  "prepared_sha256": "canonical hash of manifest.json",
  "predictions": [
    {"id": "selected task ID", "status": "completed", "output": {"answer": "B"}}
  ]
}
```

Obtain its identity using `canonical_hash(load_bundle(path)["manifest"])` from
`provenance.benchmarks`. This binds artifacts; it does not prove a model was
actually run under that condition. Preserve runtime configuration, raw outputs,
traces, costs, and failures separately when implementing execution.

```sh
uv run python -m provenance.benchmarks score \
  --prepared runs/benchmark-prepared/finqa-dev \
  --predictions runs/predictions.json --output runs/score.json
```

Unknown/duplicate IDs, incompatible manifests, changed task/input hashes, and
inputs differing from the allowlisted projection fail closed. Missing, failed,
and invalid outputs remain in the selected-task denominator. Reports preserve
source identity, input/selection identity, and submission hash. No cross-dataset
blended accuracy is produced.

- **FinEval:** strict single uppercase letter in `{"answer": "A"}`. This output
  contract is a versioned adaptation, not a claim to reproduce Salesforce's exact
  generation/extraction protocol. Upstream lowercase labels are normalized; a
  conflicting answer letter and choice index remains `requires_review`, with no
  automatic pass. Three such conflicts were found in the pinned Easy release.
- **FinQA:** adapted answer-only accuracy compares a finite predicted scalar,
  rounded with Python `round(value, 5)`, against `exe_ans`. `yes`/`no` are supported.
  No program runs and no official program/execution accuracy is claimed. There is
  no implicit percent conversion: `25` and `0.25` remain different. Execution
  targets may use a ratio where display answers use a percentage; the prompt
  documents that convention, but answer-only ambiguity remains a limitation.
  Booleans, nonfinite values, units in numeric strings, and extra output fields
  fail. Twelve pinned dev records have empty display answers but valid targets.
- **TAT-QA:** pinned official EM/F1 and separate scale accuracy. Install with
  `uv run --extra benchmark-metrics python ...` for scoring/execution. The wrapper
  converts finite JSON numbers to plain decimals, preventing the upstream parser
  from reading only the mantissa of `1e20`; scientific-notation strings and all-blank
  answer lists are invalid. Zero is preserved. Upstream magnitude equivalence,
  rounding, span normalization, and separate scale-label behavior remain; these
  metrics do not establish strict financial semantic support.
- **ConvFinQA:** adapted scalar accuracy per turn and whole-conversation success.
  Missing turns stay in the turn denominator. A failed outer conversation cannot
  pass as completed even when recorded turn answers are correct; turn credit is
  retained separately. Future questions/programs/answers remain evaluator-owned.
  Program accuracy is not implemented. The bounded runner supports both history conditions.
- **FinanceBench:** completed answers require semantic/evidence review; accuracy
  remains null, even when every run is missing. A returned passage and correct
  number alone do not establish supported-task success.

## Run a bounded tool-free development batch

Set the existing OpenRouter environment variables for the exact model and verified
conservative rates, then run:

```sh
uv run python -m provenance.benchmark_run --live \
  --prepared runs/benchmark-prepared/finqa-dev \
  --output runs/benchmark-live/finqa-pilot \
  --budget-usd 0.05 --per-task-usd 0.02
```

For single-turn datasets this makes at most one request per selected task, with no research tools or gold
references in model messages. It supports model-only, supplied-context, and
FinanceBench evidence-supplied conditions. Full-agent mode is rejected until a
verified document-corpus execution path is implemented. Each run records model,
prompt, prices, revision/dirty state, permitted input, raw response, parse status,
cost estimate, and latency. `submission.json` records every selected ID before
inference. A pending reservation survives a crash; an existing output directory
cannot be reused. Uncertain billing stops further calls. Invalid JSON and extra
output fields remain visible contract failures, without a hidden repair attempt.
Check account usage and the authorization ledger before invoking a paid batch.

## Verified development state

All 883 FinQA dev records, 150 public FinanceBench records, 1,032 CFA-Easy records,
and 90 CFA-Challenge records were schema-processed from hash-verified originals.
Prepared local selections: 100 FinQA, 100 FinanceBench evidence-supplied,
70 CFA-Easy and 30 CFA-Challenge, all seed `20261116`. Counts are preparation QA,
not attempts or financial accuracy. Selection manifests are local evaluator
artifacts. No third-party question text is redistributed in synthetic unit tests.

The [ten-task live development pilot](reports/external-pilot-2026-11-16/report.md)
now measures a small subset: five choice passes, two of three FinQA scalar passes,
and two FinanceBench responses awaiting semantic adjudication. Its conservative
cost was $0.0161622. Preserve its original failures and reference-issue findings.

Expansion verification: all 1,668 TAT-QA questions and 421 ConvFinQA conversations
(1,490 turns) imported. Official TAT-QA reference self-scoring matched all 1,668
references; this is compatibility QA, not model accuracy. All 421 conversations
overlap FinQA dev by source page. New preparations contain 100 TAT-QA questions
and 30 conversations with shared report grouping/exposure rules.

Next iterations: expanded preregistered pilots, full-document execution with exact
corpus binding, independent reviewer calibration, and source ingestion comparisons. See [loop protocol](improvement-loop.md).

## Conversation execution and document assembly

The same runner dispatches ConvFinQA preparations to a per-turn executor.
`--per-task-usd` caps an entire conversation; `--per-turn-usd` caps one request.
Every selected turn is recorded before inference. Invalid actual answers stop
agent-history conversations; reference-history can proceed with earlier gold,
explicitly labeled. Future questions and current/future gold never enter inputs.
Uncertain billing stops the batch; crashes retain pending reservations.

FinanceBench full-document acquisition is separate from execution:

```sh
uv run python -m provenance.financebench_corpus \
  --prepared runs/benchmark-prepared/financebench-full-docs-v1 \
  --metadata runs/benchmark-data/financebench-documents/financebench-documents.jsonl \
  --metadata-source runs/benchmark-data/financebench-documents/source.json \
  --output runs/financebench-full-docs-v2
```

Only selected whole PDFs and metadata enter ingestion; evaluator gold does not.
The pinned mirror revision and original/text hashes bind the corpus. Conflicting
metadata for a selected document rejects assembly; unrelated conflicts do not
block it. The upstream metadata contains conflicting 2022/2023 periods for
`FOOTLOCKER_2023_annualreport`; neither is silently chosen. The three-document
native-extraction probe completed, but pypdf reported missing fontTools for some
CFF fonts. This is an extraction-quality limitation, not a verified evidence corpus.
Full-agent paid execution remains disabled pending binding enforcement and QA.

The independent `provenance.table_structure` command produces native HTML table
sidecars with cell positions, spans, original locations, and source hashes.
It preserves empty/split-sign cells without changing legacy corpus text. It does
not infer header associations, periods, units, or financial meaning.
