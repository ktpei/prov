# TAT-QA and ConvFinQA integration research

Verified on 2026-11-16 against complete pinned development releases and official
scorer modules. This supplements [external benchmark research](external-benchmark-research.md)
and [the benchmark plan](benchmark-plan.md).

## Status and scope

The schema audit and scorer compatibility probes below are completed research.
Adapter implementation and scorer vendoring are separate work owned by the lead
and implementation worker; this document does not certify their integration.
Existing prepared core pilot artifacts remained unchanged throughout this audit.

All acquisition bytes and scorer modules used by this research were held in
memory. There are no downloaded scorer paths or research-created dataset files
to reuse. Temporary Python dependencies were resolved through `uv`; no project
dependency files were edited. No model inference ran, no inference budget was
spent, and no prepared final or original heldout cases were evaluated by a model.

Compatibility counts mean that reference answers/programs passed their own
official evaluator. They do **not** measure model quality, verify semantic
correctness of every annotation, or establish independent benchmark coverage.

## Immutable acquisition and hashes

TAT-QA revision: `870accc41953dcde885aabeb963d94aabdc0fbc3`.
ConvFinQA revision: `cf3eed2d5984960bf06bb8145bcea5e80b0222a6`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| TAT-QA `dataset_raw/tatqa_dataset_dev.json` | 1637431 | `8da095a819af6db3c14877c6df2d4d29960e41d1a63dd1fa853507bd2a616af5` |
| ConvFinQA `data.zip` | 17512756 | `d764271fae60d81b62e6d58dfc481807ebc8cfbcd633811241723c4a2101072a` |
| Archive member `data/dev.json` | 5730210 | `9665dd60f106e5cd41d37537edac97bbd26eb7629ad63ca2390b19d4619ba51b` |
| Archive member `data/dev_turn.json` | 21633236 | `8a2461be571a3277c443e2dce6e3cce6f4df197db5b7d0b60eed3477f4c952b9` |

- [TAT-QA development JSON](https://raw.githubusercontent.com/NExTplusplus/TAT-QA/870accc41953dcde885aabeb963d94aabdc0fbc3/dataset_raw/tatqa_dataset_dev.json)
- [ConvFinQA archive](https://raw.githubusercontent.com/czyssrs/ConvFinQA/cf3eed2d5984960bf06bb8145bcea5e80b0222a6/data.zip)

Archive-member hashes cover the original uncompressed bytes, not reformatted
JSON. The archive also includes `data/train.json`, `data/train_turn.json`,
`data/test_private.json`, and `data/test_turn_private.json`; the private-test
names differ from the simpler names in the README. This audit's gold consistency
and scorer probes cover development data only.

## TAT-QA complete development audit

The release contains **278 context groups and 1,668 questions**, with exactly six
questions per group. All table UIDs and question UIDs are unique. Canonical JSON
hashing found no duplicated table matrices or complete table/paragraph contexts.

Every table is nonempty, rectangular, and string-valued. There are 1,356 paragraph
records; every paragraph has nonempty text, and paragraph orders are unique
within their group. Every question has all required fields. The audit found no
empty questions, missing/empty whole answers, nonfinite arithmetic answers, or
references to nonexistent paragraph orders.

| Answer type | Questions | Actual gold value type |
| --- | ---: | --- |
| `span` | 701 | List of strings |
| `multi-span` | 217 | List of strings |
| `arithmetic` | 718 | 403 floats and 315 integers |
| `count` | 32 | String in every case; compatible with the official integer conversion |

Scale distribution: empty string 794; `million` 254; `percent` 268; `thousand`
345; `billion` 7. Empty derivations occur in 628 span and 206 multi-span questions;
all arithmetic/count derivations are present. Do not require a nonempty
derivation for every answer type.

One multi-span annotation has an empty member: question
`d47306cf-e276-4836-a827-ebebdc47e078` has three strings, with `""` at zero-based
index 2. Six annotations repeat answer spans:

- `e533cad8-8912-4956-97a8-a51179fa6a8c`
- `446acbfa-24f4-4d12-9d96-2a74ea3896a7`
- `1ae19326-ebf1-4430-b26d-bce0a211fce7`
- `38aeff11-942b-4ef1-a498-8487fa59c3db`
- `6ead824d-99aa-428a-908f-c8e435ac4431`
- `95307fa4-6c14-4d86-ba45-cd2c278a22ce`

Preserve the original lists, including empty and duplicate members, for official
metric compatibility. Do not silently repair them or reject the complete release
because a stricter generic schema assumes every member is nonempty and unique.
The unusual lists all passed reference-against-reference scoring.

### Actual schema and proposed mapping

```text
group:
  table: {uid: string, table: list[list[string]]}
  paragraphs: list[{uid: string, order: integer, text: string}]
  questions: list[question]

question:
  uid: string
  order: integer
  question: string
  answer: list[string] | float | integer | string
  derivation: string
  answer_type: string
  answer_from: string
  rel_paragraphs: list
  req_comparison: boolean
  scale: string
```

Recommended normalized mapping:

| Field | Value and boundary |
| --- | --- |
| `id` | Question UID, namespaced if required by the shared adapter interface |
| `question` | Current question text only |
| `context` | Complete table matrix and all ordered paragraphs; preserve paragraph identifiers |
| `reference` | Answer, type, source annotation, derivation, scale, relative paragraph annotations, comparison flag |
| `metadata` | `group_id = table.uid`, question order, revision, upstream split |

Keep all six questions with the same table UID in the same partition. The raw
release provides no filename or source-document ID: table UID identifies a
context, not a verified complete document. Stronger document isolation requires
additional provenance and cannot be claimed from these fields alone. Model input
must not contain sibling questions, gold scale/type, derivations, or annotated
relevant-paragraph selections. Use raw data rather than answer-derived TagOp
`facts` or `mapping` fields.

## ConvFinQA complete development audit

The conversation file contains **421 conversations and 1,490 turns**: 300 Single
conversations and 121 Double conversations. The turn file contains the same 1,490
turns: 487 `number_turn` and 1,003 `program_turn` records. All conversation IDs
and turn IDs are unique.

| Turns per conversation | Conversations |
| ---: | ---: |
| 2 | 116 |
| 3 | 94 |
| 4 | 103 |
| 5 | 88 |
| 6 | 17 |
| 7 | 2 |
| 8 | 1 |

All tables are nonempty, rectangular string matrices; all pre/post context
members are strings, with no empty pre/post lists. For every conversation,
`dialogue_break`, `turn_program`, `exe_ans_list`, and `qa_split` have equal
lengths. No question/program strings are empty and no execution gold is missing.
Execution targets comprise 1,486 finite floats and four strings: three `no` and
one `yes`.

For every turn, `cur_dial` equals the corresponding conversation question prefix,
`exe_ans` equals the matching execution-list value, and `cur_program` equals
`turn_program[turn_ind]`. Turn indices are zero-based. Thus the conversation file
is sufficient to construct equivalent turn records for the verified development
release; the turn file provides an independent alignment check.

### Actual schema and proposed mapping

All conversation records have:

```text
id: string
filename: string
pre_text: list[string]
post_text: list[string]
table: list[list[string]]
table_ori: list[list[string]]
annotation: mapping
```

Single records additionally have `qa`; Double records instead have `qa_0` and
`qa_1`. All are mappings containing original FinQA gold information and must
remain evaluator-owned.

All annotations have `amt_table`, `amt_pre_text`, and `amt_post_text` strings;
and `step_list`, `answer_list`, `dialogue_break`, `turn_program_ori`,
`dialogue_break_ori`, `turn_program`, `qa_split`, and `exe_ans_list` lists.
Single annotations have `original_program`; Double annotations have
`original_program_0`, `original_program_1`, `answer_list_0`, `answer_list_1`,
`step_list_0`, `step_list_1`, and integer `offset`.

Turn annotations add `cur_program`, `cur_dial`, `exe_ans`, `cur_type`, `turn_ind`,
and `gold_ind`. These turn records still retain complete future annotations;
they are **not safe model inputs without projection**.

Recommended evaluator-owned conversation representation:

```text
conversation_id = record.id
context = {pre_text, table, post_text}
private_turns = zip(dialogue_break, turn_program, exe_ans_list)
metadata = {filename, report_id, revision, upstream_split}
```

Project each model-visible turn explicitly:

```text
id = conversation_id + "_" + zero_based_turn_index
question = private_turns[index].question
context = frozen report context
history = previous questions plus permitted previous answers only
reference = {program, exe_ans}  # evaluator-owned, never model-visible
```

Reference-history exposes only earlier reference answers; actual-agent-history
uses earlier predictions. Neither condition may expose the current answer or any
future question/answer. Preserve the complete private conversation for sequencing
without serializing it into model-visible context. Report per-turn accuracy and
whole-conversation success separately.

### Verified FinQA overlap and partition implication

ConvFinQA dev contains 218 distinct `filename` source-page values and 173 distinct
`TICKER/YEAR` report prefixes. As many as five conversations share one page.
**All 421 conversations, all 218 pages, and all 173 report prefixes overlap the
pinned FinQA development release by source filename.** The comparison used the
FinQA dev artifact whose SHA-256 is
`a847fb7e0d61a3125a1e2909852df6b89f1ee64d2c5ff1bf689e332214deee51`.

Use `filename` as the minimum shared grouping key; its `TICKER/YEAR` prefix gives
stronger report isolation. Align ConvFinQA group assignments with existing FinQA
partitions instead of independently sampling a new split. If existing assignments
conflict at a stronger grouping level, resolve the partition policy explicitly
without silently changing the frozen pilot. Conversation-ID-only splitting does
not prevent shared-source leakage. These datasets do not provide independent
coverage merely because their task IDs differ.

## Official scorer modules and dependencies

| Module | Bytes | SHA-256 |
| --- | ---: | --- |
| TAT-QA `tatqa_metric.py` | 14129 | `2aeeac479f89f8c76300af1cc0e8d098eb86af84bc386b38b6ab4af484a6dea8` |
| TAT-QA `tatqa_utils.py` | 3807 | `a84bb2f960737cf0a53733637a674cc4b20ef030a2be6a4b21dc2c4356f415ec` |
| ConvFinQA `code/utils/general_utils.py` | 14388 | `bbe88b84ebe7026dc940e1c0e955cf63ac5b1082049e32f2ec1cc29482452b2d` |

- [Pinned TAT-QA metric](https://raw.githubusercontent.com/NExTplusplus/TAT-QA/870accc41953dcde885aabeb963d94aabdc0fbc3/tatqa_metric.py)
- [Pinned TAT-QA utilities](https://raw.githubusercontent.com/NExTplusplus/TAT-QA/870accc41953dcde885aabeb963d94aabdc0fbc3/tatqa_utils.py)
- [Pinned ConvFinQA scorer](https://raw.githubusercontent.com/czyssrs/ConvFinQA/cf3eed2d5984960bf06bb8145bcea5e80b0222a6/code/utils/general_utils.py)

`tatqa_metric.py` imports `typing.Set`, `typing.Tuple`, `typing.Union`,
`tatqa_utils.*`, pandas, NumPy, and `scipy.optimize.linear_sum_assignment`.
`tatqa_utils.py` imports `re`, `string`, `typing.List`, and NumPy. No other local
module is required. Vendoring both under a package requires adapting the metric
import to `from .tatqa_utils import *`; record that one-line packaging change and
retain original source hashes separately from modified-file hashes.

The ConvFinQA scorer imports the standard library, NumPy, and
`sympy.simplify`; it requires no sibling module for the tested functions. Neither
scorer requires Torch, Transformers, TensorFlow, or AllenNLP. TAT-QA's legacy
training `requirement.txt` is not a minimal scorer environment and does not
directly pin SciPy despite its use in the metric.

Compatibility probes passed with these exact installed versions:

| Dependency | Version |
| --- | --- |
| Python | 3.13.2 |
| NumPy | 2.5.5 |
| pandas | 3.1.1 |
| SciPy | 1.18.1 |
| SymPy | 1.14.0 |

These are a verified probe environment, not a project dependency decision or
proof of compatibility with every alternative version.

### Successful call interfaces and results

TAT-QA interfaces used:

```python
metric = TaTQAEmAndF1()
metric(
    ground_truth,
    prediction,
    pred_scale="",
    pred_span=None,
    gold_span=None,
    pred_op=None,
    gold_op=None,
)
metric.get_overall_metric(reset=False)  # EM, F1, scale accuracy, operation accuracy
metric.get_raw()                       # per-question details
```

The probe passed each reference answer as the prediction with its reference
scale. Lists were retained unchanged; scalar values were converted to strings.
All **1,668** questions received **EM=1 and F1=1**, with no exceptions. Scale
accuracy was 1; operation accuracy was 0 because operation predictions were not
provided. This was a scorer/annotation consistency check, not an inference run.

The scalar conversion matters: the wrapper treats numeric `0` as falsey. Pass
`"0"` or `["0"]` for a valid zero prediction. A suitable output contract is a
scalar string or list of strings, plus one of the five observed scale labels.
The official evaluator performs scale-aware normalization, sorts/joins spans,
and forces arithmetic/count F1 to equal EM. Do not replace those rules with a
generic numeric tolerance or generic token F1 while calling the result official.

ConvFinQA interfaces used:

```python
tokens = program_tokenization(original_program)
invalid_flag, result = eval_program(tokens, table)
equivalent = equal_program(gold_tokens, prediction_tokens)
```

All **1,490** reference programs executed without invalid flags, exactly matched
their execution gold, and passed symbolic self-equivalence. Every projected turn
also matched the independent turn release. Again, these are compatibility
counts, not model performance.

Official execution rounds final numeric results to five decimal places and
compares them to execution gold; yes/no remains string-valued. Single-number
programs are supported. Preserve the program tokenizer's syntax and explicit
`EOF` terminator. Numeric answer-only grading remains an adaptation and cannot
establish program accuracy.

Avoid using ConvFinQA's batch `evaluate_result` directly as the integration
boundary: it reads reference programs from the prediction-file structure, writes
result/error files, mutates records, divides by submitted prediction count, and
asserts that symbolic correctness implies matching execution. Build reference
programs from evaluator-owned data. Independently validate complete expected IDs,
prediction structure, finite outputs, and bounded computation. Do not permit
model-supplied `ref_prog` to define its own correctness.

## Attribution and vendoring

These are upstream license declarations and implementation recommendations,
not a determination of every possible downstream use.

| License file | Bytes | SHA-256 |
| --- | ---: | --- |
| TAT-QA `LICENSE` | 1068 | `46e27ffbc49c3fd44a9595c2213f8a5f4319a81b53238e49ce1eec39e7e25662` |
| ConvFinQA `LICENSE` | 1067 | `5c7b6fe25d37f4b6cc7e0e76267bce7146765b7661d4bb0e9ecc4eb0ed34fb4c` |

Both code licenses are MIT. Copies/substantial portions should retain the
complete applicable copyright and license notice:

- TAT-QA: Copyright (c) 2021 Fengbin Zhu. [Pinned license](https://raw.githubusercontent.com/NExTplusplus/TAT-QA/870accc41953dcde885aabeb963d94aabdc0fbc3/LICENSE)
- ConvFinQA: Copyright (c) 2022 Zhiyu Chen. [Pinned license](https://raw.githubusercontent.com/czyssrs/ConvFinQA/cf3eed2d5984960bf06bb8145bcea5e80b0222a6/LICENSE)

TAT-QA **dataset** licensing is separately CC BY 4.0, as stated in its
[README](https://github.com/NExTplusplus/TAT-QA/blob/870accc41953dcde885aabeb963d94aabdc0fbc3/README.md).
When sharing adapted data, identify the dataset/authors, link the source and
license, and identify modifications according to the [CC BY terms](https://creativecommons.org/licenses/by/4.0/).
Keep dataset and code attribution separate; do not infer rights in source reports
solely from a code license.

Recommended integration: inspect and vendor only the small pinned scorer modules
and their license notices, record source and local hashes, and keep downloaded
datasets outside committed fixtures. Do not execute remote branch-head code or
download scorer modules at scoring runtime. A dynamic acquisition alternative
would still need immutable hash checks and retained notices, but it is not
required for this integration. The research's in-memory loading was a controlled
compatibility probe, not a proposed runtime architecture.
