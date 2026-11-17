# Frozen harness evaluation — 2026-11-07

**Four of six fresh tasks met the preregistered evidence-supported task criteria
(66.7%) under coding-agent review.** Five returned final answers. The unchanged
mechanical grader passed two. These are results on six public development
questions about one company, not a general financial-research accuracy estimate
or independent human financial validation.

The runtime, prompts, retrieval, source packet, and grader were unchanged during
evaluation. No failed task was rerun and no scoring keys were revised afterward.
The original 15-task holdout was not run or used for tuning.

## Result dimensions

| Measurement | Result | Meaning |
| --- | ---: | --- |
| Fresh tasks attempted | 6/6 | All preregistered questions, once, in ID order |
| Final answers returned | 5/6 | One stopped without an accepted answer |
| Correct core responses, coding-agent review | 5/6 | Includes one correct abstention without a source read |
| Evidence-supported task passes, coding-agent review | **4/6** | Every requested finding correct with sufficient cited context; no material unsupported addition |
| Unchanged mechanical passes | 2/6 | Exact period strings reject two substantively correct numerical answers |
| Complete trace/read/quote checks passed | 4/6 | Stopped task and search-only abstention fail |
| Required numerical values correct in returned numerical answers | 4/4 values across 2 tasks | Conditional on returned answers; not a success rate over all 3 numerical tasks |
| Tool errors | 1/41 (2.44%) | An 81-line read was rejected; the model recovered |
| Fresh fixed-query retrieval anchor coverage | 4/5 positive-evidence tasks | Evaluator-authored queries, not autonomous answer accuracy |
| Fresh extraction anchor coverage | 5/5 positive-evidence tasks | Text present; not proof of complete chart/table extraction |
| Existing fixed-query retrieval reproduced | 6/8 positive-evidence tasks | Separate older development suite |

Strict task review follows the [preregistered protocol](protocol.md). A supported
extra number omitted from structured claims is recorded as an output-contract
defect, distinct from an unsupported factual claim. Do not relabel the 4/6 task
result as full compliance with every runtime instruction: fresh-03 has that defect.
The five correct core responses likewise do not mean five evidence-backed passes.

## Per-task outcomes

| Task | Final answer | Mechanical | Evidence-supported task review | Finding |
| --- | --- | --- | --- | --- |
| fresh-01: GAAP/non-GAAP R&D | Stopped | Fail | **Fail** | Draft had correct amounts but altered table separators in quotes; rejected. Repair then hit spending-reservation limit before another provider response. No accepted answer. |
| fresh-02: current assets, liabilities, difference | Returned | Fail | **Pass** | 2163.878 − 641.615 = 1522.263 USD million; headers and rows cited. Exact grader expects `September 30, 2024`, while claims use runtime-canonical `Q3 2024`; narrative and header correctly identify the as-of date. |
| fresh-03: nine-month PPE purchases | Returned | Fail | **Pass, output-contract defect** | Correct positive outflow magnitude, 111.884 USD million, with nine-month 2024 and thousands headers. Period mismatch is capitalization only. Supported 2023 comparison appears in prose without its own structured claim. |
| fresh-04: dividend policy | Returned | Pass | **Pass** | Correctly attributes no prior cash dividends, retention of future earnings for operations/expansion, and no expected dividends for the foreseeable future. |
| fresh-05: R2, D1, Workers | Returned | Pass | **Pass** | Correctly attributes R2 dataset movement/training gateway, D1's SQL role, and full application primitives to management. Extra product-primitives discussion is supported by the cited continuation. |
| fresh-06: Germany employee count | Returned | Fail | **Fail; core abstention correct** | No country count invented, but all 12 tools were searches and none was a read. It asserts packet contents from snippets; evaluator rejects `No evidence was read`. |

### Evidence and failure detail

**fresh-01:** Release L225 and L227-L228 provide units/columns; L247-L249 contain
R&D and the stock-compensation adjustment. The first draft rewrites
`GAAP research and development | | $ | 110,911` as
`GAAP research and development | $ | 110,911`, and similarly changes non-GAAP
separators. The runtime correctly rejects non-exact quotes. After one permitted
repair, a fifth model step requires a $0.0370548 reservation on top of $0.0153972
already accounted, totaling $0.052452 against the $0.05 per-task cap. No fifth
provider response occurs. This is a reservation/headroom failure, not $0.05 in
actual recorded usage or proof that the numerical extraction was wrong.

**fresh-02:** Release L129/L131 establish thousands and September 30, 2024;
L140/L156 provide the current totals. Returned cited spans jointly cover the date,
units, and both inputs. Decimal subtraction independently agrees. Mechanical
failure is the exact period string, not the amounts, units, arithmetic, or actual
as-of date. This adjudication does not change the saved mechanical failure.

**fresh-03:** Release L172-L175 provide thousands and nine-month 2024 columns;
L202 gives `(111,884)` and the 2023 comparison `(83,580)`. The answer correctly
reports a positive cash-outflow magnitude. Returned `Nine Months Ended September
30, 2024` differs only in capitalization from the key. Its unstructured 2023
comparison remains an instruction-following defect even though the cited span
supports the number. An invalid L200-L280 read spans 81 lines; the 80-line limit
rejects it and a later L162-L210 read recovers the full relevant context.

**fresh-04:** Filing L1620-L1621 supports every requested policy finding and the
supplementary stockholder-return statement. The answer retains the foreseeable-
future qualification. It nevertheless uses all 10 model turns and 11 tools for
one short source passage, an efficiency issue worth addressing later.

**fresh-05:** Transcript L697-L704 supports R2, L705-L708 supports D1 and the
Workers application explanation, and L709-L712 supports the extra product
primitives. The claims are attributed to Prince rather than independently proved
performance. No invented adoption/performance figures appear.

**fresh-06:** The requested Germany headcount is absent from the reviewed packet;
filing L1197's worldwide total is not a substitute. The response correctly declines
to invent a figure, but never invokes `read_source`. Its scoped inability is useful;
its assertion about what the packet discloses lacks read-evidence verification.
This remains a failure under the registered evidence requirement.

## Runtime and spending

| Measurement | Fresh batch |
| --- | ---: |
| Estimated accounted cost | **$0.0863112** |
| Estimated cost per registered task | $0.0143852 |
| Combined with prior cloud development | **$0.4362039**, below $0.50 authorization |
| Input/output tokens | 118,940 / 6,228 |
| Model steps / recorded provider responses | 34 / 33 |
| Tool calls / errors | 41 / 1 |
| Sum of per-task harness latencies | 50.75 seconds |
| Mean / median per-task latency | 8.46 / 8.38 seconds |
| Uncertain-cost flags | 0 |

Model: `deepseek/deepseek-v4.1-flash-1017`. Temperature 0, 4,000 maximum output
tokens, 10 model turns, 12 tool calls, 180-second task deadline and 45-second request
timeout. Global experiment cap $0.15; each task cap $0.05. No Exa/OCR/paid judge or
model substitution. No task was skipped for aggregate exhaustion.

Accounting used $0.60 input/$2.40 output per million tokens, the highest advertised
endpoint rates at preflight; the [public endpoint source](https://openrouter.ai/api/v1/models/deepseek/deepseek-v4.1-flash-1017/endpoints)
and all 50 endpoint prices are preserved in [preflight.json](preflight.json).
Prior cloud development used different $0.30/$1.20 assumptions; the combined total
sums those respective estimates. These are conservative application token-rate
estimates, not provider invoices or a guaranteed account billing cap. Provider
routing was unchanged and not pinned; temperature 0 does not guarantee identical
future responses. `model_calls` includes a reservation-blocked step, so it is not
the number of completed paid requests. Latency is local harness time on this Mac.

## Reproducibility and frozen boundaries

- Preregistration commit: `ce1a2f249dd7d907ac5570d5284dbc371878032a`.
- Runtime baseline: `d9057ed7e1800964ed71838e324b2d4760d2e9d6`; no research code,
  dependency lock, source packet, or original benchmark changes in this evaluation.
- Task SHA256: `a6b6a78d0da423da3bafa3049adb1b0baca96c90f63f256612a605bc6532ea5d`.
- Experiment began with a clean working tree. All six task IDs were attempted
  once, in the registered order. All saved fresh grades reproduce offline.
- [Summary](summary.json), [experiment ledger](fresh-run/experiment.json), and
  individual `fresh-run/fresh-*.json` files preserve public answers, complete events,
  metrics, stop reasons, source hashes, and revision identity. Original ignored
  `trace_path` entries are diagnostic paths; embedded events enable portable replay.
- Separate coding agents authored/checked questions and reviewed final answers;
  the lead inspected source spans, arithmetic, traces, and actual artifacts.
  This is coding-agent textual review, not independent human financial validation.
- Local `yarn lint` and all **79 tests** pass. Python 3.13 test execution still
  reports existing unclosed SQLite connection warnings; no cleanup fix was mixed
  into the scored runtime. Passing tests are software verification, not accuracy.

Offline reproduction (no credentials, model calls, or charges):

```sh
uv sync --locked
yarn lint
yarn test
uv run python -m provenance.evaluation --corpus data/cloudflare-2024-q3 \
  --benchmark eval/company_fresh_tasks.json
uv run python -m provenance.evaluation --corpus data/cloudflare-2024-q3 \
  --benchmark eval/company_fresh_tasks.json --task fresh-02 \
  --result eval/reports/frozen-evaluation-2026-11-07/fresh-run/fresh-02.json
```

Repeat the last command for other task IDs/results to inspect unchanged mechanical
outcomes. Historical 28-run mechanical replay and the four selected rerun audit
are [separate artifacts](historical-review.md); their best results are not mixed
into this fresh score. The fresh [fixed-query report](fresh-retrieval.json) misses
complete cash-flow header/row anchor coverage in fresh-03, despite all anchors
existing in extraction. The autonomous model recovers those lines through reads;
fixed-query coverage and model success are distinct measurements.

## What to do next

1. **Reserve synthesis/repair headroom deliberately.** Reproduce fresh-01's blocked
   final step before changing budget/context policy; do not solve it merely by
   reporting an unaccepted draft as a success.
2. **Make evidence requirements consistent for abstentions.** Add a read-evidence
   check before final completion, and distinguish “could not establish” from an
   exhaustive claim about all documents. Preserve the search-only failure here.
3. **Version semantic-aware period grading.** Recognize capitalization and explicit
   as-of dates without conflating quarters, forecasts, or stock/flow periods.
   Preserve this grader and its 2/6 result; test any future grader independently.
4. **Check narrative/claim completeness.** Every additional financial number should
   have a structured claim and supporting context, or be omitted. Retain table
   headers with values and preserve qualifiers such as “nearly.”
5. **Replace the now-inspected fresh suite for the next assessment.** First add
   further companies/documents, fresh cross-source and deck/table questions, more
   abstention types, and independently authored tasks. Arrange human financial
   review before claiming general accuracy or deployment readiness. Keep the
   original holdout separate until a final evaluation is explicitly authorized.

These are follow-up recommendations, not changes applied during this evaluation.
Six tasks from one previously inspected company corpus cannot estimate production
accuracy, parser/OCR reliability, chart understanding, or financial-domain
generalization. This measured baseline identifies specific failure modes while
preserving both the successful answers and the failures.
