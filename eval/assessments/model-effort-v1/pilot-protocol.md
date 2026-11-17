# Model/effort v1: frozen supplied-evidence diagnostic

Freeze before any inference. Runtime implementation: `01983f4`; its
[infrastructure acceptance](infrastructure-report.md) establishes accounting and
failure handling, not model effectiveness. Exact inputs, configurations and rubric
are bound by [pilot-bindings.json](pilot-bindings.json).

## Selection and reference review

Select four IDs from the six previously exposed development cases in the
FinanceBench context-v1 protocol by ascending SHA-256 of compact JSON
`["model-effort-v1",17,id]`. Selection uses identity metadata, not outputs.
The selected cases are Costco 04209, 3M 01865, American Water Works 04254,
and Verizon 00215. All six reserved validation issuers remain unopened;
Amazon/Microsoft prior-exposure dispositions remain unchanged.

Preparation uses seed 17, the existing development exposure groups, and
`evidence_supplied`. This measures interpretation with the evidence provided,
not retrieval, a full-agent workflow, or unseen-issuer generalization.
The original local prepared bundle remains immutable. The reviewed bundle at
`runs/model-effort-v1/prepared-reviewed` preserves its model inputs exactly.

An independent coding-agent review froze [rubric.json](rubric.json) before
seeing outputs or arm identities. Exclude 3M without replacement: the gold
implicitly excludes currency alongside M&A, while the question does not clearly
request that. A content-bound entry in `eval/reference-issues.json` retains the
original reference and flags the ambiguity. All 16 selected task/arm rows remain
in the ledger; four are excluded before dispatch. Report three adjudicable cases
per arm and the exclusion separately, never as four successful cases.

## Arms, controls and stopping rules

Compare exact `deepseek/deepseek-v4.1-flash-1017` and `openai/gpt-6-luna`, each
at explicit low and high reasoning effort. [arms.json](arms.json) pins provider,
model response identities and conservative published reservation rates.
Temperature is omitted for every arm. Common completion ceiling: 8,192 tokens;
common timeout: 120 seconds. Identical supplied evidence and instructions;
no tools, no retry, no provider fallback. One sample per included case per arm.
Run task-major with rotating arm order, as implemented by the frozen runner.

Maximum pilot spend is $0.40 total, $0.10 per arm, $0.025 per attempt. The
historical conservative ledger total is $0.4814193 against the $1 authorization.
Refresh the key budget before dispatch. Preserve all failures and exclusions.
Uncertain billing or identity/integrity mismatch stops the entire comparison.
Do not repair configuration and silently rerun failures under this protocol.
Output directory: `runs/model-effort-v1/results`; reuse/resume is prohibited.

## Evaluation and interpretation

Persist original raw answers before grading. Review anonymized answers against
the frozen rubric without model/effort identities, cost or latency. Grade
correctness, financial interpretation, arithmetic, units/period, citation support,
unsupported claims and abstention separately. Do not rewrite answers or substitute
model consensus for evidence. FinanceBench automatic semantic success remains
null; the descriptive review is not calibrated human finance validation.

Report all attempted rows, complete versus failed outputs, excluded rows,
review coverage, per-arm cost, latency, usage and reasoning tokens. Reasoning
tokens are part of completion billing, not an additional charge. Retain cache
usage where supplied; sequential interleaving does not remove all latency/cache
confounding. Three exposed cases and one sample cannot establish a reliable
ranking, statistical superiority or production promotion. A successful run is a
compatibility/measurement pilot and informs the next frozen development trial.
