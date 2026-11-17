# External finance benchmark research

Verified on 2026-11-16 against primary upstream repositories, dataset cards,
released records, and evaluator source. This is a research record supporting
[the benchmark plan](benchmark-plan.md), not a benchmark result or a claim that
the proposed integrations are complete.

## Status and authorization boundary

- **Verified research:** upstream revisions, core release file hashes, schema
  examples, license declarations, metric behavior, and the complete-release
  import findings described below.
- **Verified local preparation:** 70 CFA-Easy, 30 CFA-Challenge, 100 FinQA,
  and 100 FinanceBench evidence-supplied tasks are prepared under
  `runs/benchmark-prepared/`. All selected IDs belong to development partitions.
  These are prepared inputs, not executed model runs or benchmark scores.
- **Implementation update:** the core adapters, acquisition, preparation/scoring,
  and tool-free runner passed lead review and repository checks. See
  [the workflow](external-benchmarks.md) and [pilot report](reports/external-pilot-2026-11-16/report.md)
  for measured status; research findings alone do not establish model accuracy.
- **Future work:** TAT-QA and ConvFinQA integration, program scoring, calibrated
  semantic review, and paid model assessment remain separate work.

Initial research fetched upstream artifacts into memory to inspect their schema
and identity. Subsequent local preparation downloaded data under
`runs/benchmark-data/`; the import audit below independently checked the FinQA
dev JSON and CFA-Easy parquet against the recorded hashes. No inference ran or
inference budget was spent. No existing 15-task heldout case was evaluated.

Preserve the existing 25-task corpus and its 10-development/15-heldout boundary.
No historical spending authorization is renewed by this document. Before a paid
run, verify remaining account usage and current prices; predeclare a finite
budget, per-task limits, retry policy, model settings, and stop conditions. Count
failed and stopped attempts. The sample targets in the plan are coverage targets,
not authorization to consume heldout cases or make statistical claims.

## Pinned releases and acquisition

| Dataset | Repository revision | Verified release detail |
| --- | --- | --- |
| Salesforce FinEval | `a911ec4dbd635228f216349c2f4eda8354ed15cc` | CFA-Easy: 1,032 test rows; CFA-Challenge: 90 test rows |
| FinQA | `0f16e2867befa6840783e58be38c9efb9229d742` | Dev: 883 rows; public test: 1,147 rows; separate private test lacks gold |
| FinanceBench | `cc39aeb4afdf33909ee1412188bf89035950c2eb` | 150 question records and 361 document metadata records |
| TAT-QA | `870accc41953dcde885aabeb963d94aabdc0fbc3` | Raw structured contexts; test gold released January 2024 |
| ConvFinQA | `cf3eed2d5984960bf06bb8145bcea5e80b0222a6` | `data.zip` contains train/dev and private-test files; dev has 421 conversations |

Use immutable revision URLs, not moving `main`/`master` references, for acquisition:

- [CFA-Easy parquet](https://huggingface.co/datasets/Salesforce/FinEval/resolve/a911ec4dbd635228f216349c2f4eda8354ed15cc/CFA-Easy/test-00000-of-00001.parquet)
- [CFA-Challenge parquet](https://huggingface.co/datasets/Salesforce/FinEval/resolve/a911ec4dbd635228f216349c2f4eda8354ed15cc/CFA-Challenge/test-00000-of-00001.parquet)
- [FinQA dev JSON](https://raw.githubusercontent.com/czyssrs/FinQA/0f16e2867befa6840783e58be38c9efb9229d742/dataset/dev.json)
- [FinQA public test JSON](https://raw.githubusercontent.com/czyssrs/FinQA/0f16e2867befa6840783e58be38c9efb9229d742/dataset/test.json)
- [FinanceBench question JSONL](https://raw.githubusercontent.com/patronus-ai/financebench/cc39aeb4afdf33909ee1412188bf89035950c2eb/data/financebench_open_source.jsonl)
- [FinanceBench document metadata JSONL](https://raw.githubusercontent.com/patronus-ai/financebench/cc39aeb4afdf33909ee1412188bf89035950c2eb/data/financebench_document_information.jsonl)
- [TAT-QA raw dataset directory](https://github.com/NExTplusplus/TAT-QA/tree/870accc41953dcde885aabeb963d94aabdc0fbc3/dataset_raw)
- [ConvFinQA archive](https://raw.githubusercontent.com/czyssrs/ConvFinQA/cf3eed2d5984960bf06bb8145bcea5e80b0222a6/data.zip)

The following SHA-256 values were calculated from immutable upstream file bytes,
not from reformatted or normalized records:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| CFA-Easy parquet | 285358 | `cd6005e33184b7e21d6735371ff82f7018fa67bca673ad26cb3e5803de4dfa0c` |
| CFA-Challenge parquet | 77056 | `f2ba5573260b19de88bc9546b2684dfe7da6de5e4d40676aa4601962aa331fb9` |
| FinQA dev JSON | 10954658 | `a847fb7e0d61a3125a1e2909852df6b89f1ee64d2c5ff1bf689e332214deee51` |
| FinQA public test JSON | 14395143 | `831dbfb2e785dbc227f895ce3f24046433467aec67b09db2bd6ac7692a8a30dc` |
| FinanceBench question JSONL | 929848 | `a5a2aa673e573e55675fc3c0f9aa38c1cf59d2abc91edb077534f71f10a71877` |
| FinanceBench metadata JSONL | 88781 | `1c69127783879de8cdadb159d2181f39bc3123b8e0ebf74031c3969d69189575` |

TAT-QA and ConvFinQA file hashes have not been recorded here; compute and pin
them before importing those releases. Hash normalized records separately from
their acquisition files when conversion is required.

## Complete-release import audit

Verified against the pinned local acquisition files on 2026-11-16, without
including question text or deciding answer correctness from domain knowledge:

| Release | Verified finding | Current handling, pending final integration review |
| --- | --- | --- |
| FinQA dev, all 883 records | 12 records have an empty `qa.answer`; none omit that field, and every record has `qa.exe_ans` | The adapter accepts a missing or empty display answer when execution gold is valid; it preserves the display field and scores against execution gold |
| CFA-Easy, all 1,032 records | Four answer labels are lowercase: three `a` and one `c` | Case normalization is valid for label comparison, but cannot resolve a disagreement with the indexed choice |
| CFA-Easy zero-based rows 470, 837, 848 | Each has `answer: "a"`, `gold: 2`, and `choices: ["A", "B", "C"]`; normalized label A conflicts with indexed choice C | The adapter preserves the label and index, marks `requires_review`, and scoring returns `passed: null` with `reference_conflict_requires_review` |

The FinQA and CFA-Easy local bytes match the respective SHA-256 values above.
The three CFA contradictions are upstream reference conflicts, not established
model errors or evidence that either label is correct. Do not silently choose
the letter, the index, or an answer inferred from financial knowledge. Keep
conflicts visible and unscored until a documented reference review resolves them;
report unscored/conflicted counts alongside the selected-task denominator.

The prepared development selections contain 100 combined CFA questions, 100
FinQA supplied-context questions, and 100 FinanceBench oracle questions. The
FinanceBench figure is current preparation coverage, not completion of the
plan's 150-case target across partitions. Preparation and import validation do
not establish model capability or consume final cases through inference.

## License declarations

These are verified upstream declarations, not a determination that a particular
commercial use or redistribution is authorized.

| Release | Declaration and qualification |
| --- | --- |
| Salesforce FinEval | [Dataset card](https://huggingface.co/datasets/Salesforce/FinEval) declares CC BY-NC 4.0 and says users must assess underlying dataset terms; release is for research supporting the paper |
| FinQA | [Repository LICENSE](https://github.com/czyssrs/FinQA/blob/0f16e2867befa6840783e58be38c9efb9229d742/LICENSE) is MIT; retain attribution and distinguish the repository license from rights in source reports |
| FinanceBench | [Official dataset card](https://huggingface.co/datasets/PatronusAI/financebench) declares CC BY-NC 4.0; [publisher research page](https://www.patronus.ai/research/financebench) explicitly describes the public sample as noncommercial |
| TAT-QA | [README](https://github.com/NExTplusplus/TAT-QA/blob/870accc41953dcde885aabeb963d94aabdc0fbc3/README.md) declares the **dataset CC BY 4.0**; root code LICENSE is MIT |
| ConvFinQA | [Repository LICENSE](https://github.com/czyssrs/ConvFinQA/blob/cf3eed2d5984960bf06bb8145bcea5e80b0222a6/LICENSE) is MIT; retain attribution and distinguish source-report rights |

Keep licensed raw datasets and answer keys out of committed fixtures. Synthetic
schema fixtures and acquisition manifests can exercise adapters without copying
released question content. Public availability alone is not permission for
commercial use or redistribution.

## Core schemas, leakage boundaries, and metrics

### Salesforce FinEval CFA subsets

Verified Easy fields are `query`, `answer`, `text`, `choices`, `gold`.
`choices` contains labels such as `["A", "B", "C"]`; option text is embedded in
`query`. `gold` is a zero-based index and `answer` is a letter. Challenge fields
are only `query`, `answer`, `source`. Neither subset provides an explicit row ID.
Use revision/subset/split/index and a content hash for stable identification.
Only the query and explicitly permitted choices belong in model input.

The [official FinDAP integration example](https://github.com/SalesforceAIResearch/FinDAP/blob/2290945a3706fca535b49dcd76871dc03358f317/README.md)
uses `query` as input, `answer` as target, and exact match ignoring case and
punctuation. Its prompt requests an explanation plus a marked selection, but the
shown configuration does not define a corresponding extraction filter. Therefore
a strict single-choice extractor must be versioned and labeled as an adaptation;
do not claim the example establishes a complete official extraction protocol.

Recommendation: reject ambiguous/conflicting choices rather than search the
entire answer for a correct letter. Predeclare internal development/final groups
because these releases expose only test splits. Challenge rows share scenarios;
keep related scenarios together where possible to avoid tuning leakage.

### FinQA

Allowlist `qa.question`, `pre_text`, `table`, and `post_text` for model input.
Keep `qa.answer`, `exe_ans`, programs, steps, annotated rows, `gold_inds`,
`model_input`, and precomputed retrieval outputs evaluator-only. The
[README](https://github.com/czyssrs/FinQA/blob/0f16e2867befa6840783e58be38c9efb9229d742/README.md)
documents an earlier table-formatting bug that leaked labels; render all rows
uniformly. Full supplied report context is an adapted condition distinct from
the end-to-end retrieval/program challenge.

The [official evaluator](https://github.com/czyssrs/FinQA/blob/0f16e2867befa6840783e58be38c9efb9229d742/code/evaluate/evaluate.py)
executes predicted programs, rounds the final numeric result with Python
`round(result, 5)`, and compares to `qa.exe_ans` using exact equality. Yes/no
outputs remain strings. Program accuracy uses symbolic equivalence, not literal
token equality. Dev targets comprise 873 floats and 10 yes/no values; public
test targets comprise 1,127 floats and 20 yes/no values.

Recommendation: answer-only scoring should target `exe_ans`, which may contain a
ratio while `qa.answer` expresses a percentage. Explicitly version accepted
formatting, percent conversion, and rounding. Name the result adapted answer
accuracy, not official execution or program accuracy. Enforce the complete
expected ID set externally: the released batch scorer divides by submitted
predictions, which otherwise permits omission-biased scores.

### FinanceBench

Verified JSONL differs from its [README schema](https://github.com/patronus-ai/financebench/blob/cc39aeb4afdf33909ee1412188bf89035950c2eb/README.md):
`financebench_id` is a **string**, evidence uses **`doc_name`**, and document
metadata uses `gics_sector`. Evidence pages are **zero-indexed**. An evidence
record includes `evidence_text`, `doc_name`, `evidence_page_num`, and
`evidence_text_full_page`. Validate actual release records rather than assuming
the README's stated integer ID or `evidence_doc_name` field.

Keep answers, justifications, reasoning labels, and gold evidence out of full-agent
input and retrieval storage. The evidence-supplied diagnostic may expose chosen
passages, with its condition explicitly recorded. Freeze source PDFs and their
extraction/page mapping separately from question records. The published work
used manual answer review; deterministic text/numeric matching alone is not an
official FinanceBench success score.

Recommendation: predeclare development/final groups within the 150 public cases,
preferably by related document/company packet. Coverage across all 150 cases
does not make a later rerun heldout. Keep strict supported-task success pending
semantic review; source identity, quote fidelity, and numeric agreement do not
establish entailment or completeness by themselves.

## Future TAT-QA and ConvFinQA integration

### TAT-QA

Use `dataset_raw`, preserving `table.uid`, the table matrix, ordered paragraph
records, and question UIDs. Separate question text from `answer`, `derivation`,
`answer_type`, `answer_from`, `rel_paragraphs`, and `scale`. Do not use
answer-derived TagOp `facts`/`mapping` as ordinary model inputs. The released
`tatqa_dataset_test_gold.json` enables offline test scoring; respect the original
split and freeze the selection before model changes.

The [official metric](https://github.com/NExTplusplus/TAT-QA/blob/870accc41953dcde885aabeb963d94aabdc0fbc3/tatqa_metric.py)
implements scale-aware EM/F1, sorts and joins answer spans, and sets arithmetic
and count F1 equal to EM. Scale accuracy is distinct from answer accuracy.
Its wrapper treats numeric `0` as falsey: convert legitimate zero predictions
to `"0"` or `["0"]` before calling it. Pin the metric together with its
[numeric normalization utilities](https://github.com/NExTplusplus/TAT-QA/blob/870accc41953dcde885aabeb963d94aabdc0fbc3/tatqa_utils.py).
Do not silently replace official rounding or percentage conventions with a
generic tolerance. Report stricter financial checks separately.

Proposed acceptance: synthetic and released development cases agree with the
pinned evaluator for spans, multi-spans, zero, negative numbers, scale
equivalents, and percentages. Structured table accuracy does not measure PDF/OCR
accuracy.

### ConvFinQA

The [release documentation](https://github.com/czyssrs/ConvFinQA/blob/cf3eed2d5984960bf06bb8145bcea5e80b0222a6/README.md)
describes conversation and turn formats. Actual archive paths include
`data/dev.json`, `data/dev_turn.json`, `data/test_private.json`, and
`data/test_turn_private.json`; do not assume the README's `test.json` exists.
Private test lacks gold; use dev for local scored pilots and label any frozen
internal partition accordingly.

Question turns live in `annotation.dialogue_break`; reference execution results
live in `annotation.exe_ans_list`. Programs, answer lists, annotation helper
fields, and original FinQA `qa`/`qa_0`/`qa_1` records contain gold. Whitelist
current/past questions and the prior answers appropriate to the chosen history
condition; never serialize all annotations. The
[official scorer](https://github.com/czyssrs/ConvFinQA/blob/cf3eed2d5984960bf06bb8145bcea5e80b0222a6/code/utils/general_utils.py)
supports single-number programs and rounds final numeric results to five places.

Proposed acceptance: separate reference-history and actual-agent-history runs;
report per-turn accuracy, whole-conversation success, and failure propagation.
Keep every conversation together across partitions. Audit original question and
document overlap with FinQA before claiming independent coverage.

## Minimal recommended portable contract

Keep the benchmark interface separate from `provenance.evaluation.grade()`, whose
existing frozen-corpus trace, citation, quote, and evidence-read requirements
serve a different purpose. Preserve that evaluator and its historical artifacts.

| Record | Required responsibility |
| --- | --- |
| Manifest | Dataset/subset, revision, upstream split, internal partition, exact IDs, sampling seed, acquisition URLs/hashes, licenses, adapter/scorer versions, condition |
| Model-visible task | ID, question, permitted structured context or source identifiers, explicitly bounded conversation history |
| Private reference | Gold answer/program, evidence annotations, derivation, scale, rubric; inaccessible to model and tools |
| Result | Raw output, extracted answer, extraction/completion status, per-metric result or `not_scored`, failure reasons, model/settings, trace, cost, latency, termination reason |

Use a fixed selected task set as the denominator, including missing, failed, and
stopped attempts. Preserve raw outputs for rescoring without paid reruns. Do not
merge benchmarks or conditions into one headline accuracy. Schema failure and
finance knowledge failure should remain distinguishable.

Before trusting scores, exercise malformed JSON; duplicate/missing/unknown IDs;
empty/conflicting choices; boolean-as-number; nonfinite numbers; ratio/percent/
percentage-point confusion; comma formatting; negative parentheses; rounding
boundaries; wrong units/periods; duplicate claim matching; identical numbers from
irrelevant sources; incomplete evidence; unsupported additions; and future-turn
or annotation leakage. Mechanical checks cannot replace calibrated human or
semantic review of financial meaning and evidence support.
