# Provenance company research harness

A read-only company research agent with LangChain + LangGraph, OpenRouter,
structured document ingestion, passage search/read, and independent evaluation.
The model chooses its research steps; deterministic code enforces budgets, call
counts, deadlines, and citation validity. The original custom loop and 25-task
public-data evaluation remain regression baselines.

This implements the initial foundation of **brief 1**, the finance agent
harness, from the [Provenance × Tech@NYU brief](https://claude.ai/artifact/3cSNqEgPBvGGNVjAj2vjcH).
The full sponsor ask includes 5–7 tools and measured evaluation results; these
remain broader than the current two-tool implementation. [project.md](project.md)
also records the deal-agent and alternative briefs for context, shared ground
rules, and semester deliverables.

## Planning documents

- [Product specification](spec.md) covers the research workflow, company-data
  proposal, module contracts, evaluation, web MVP, and later live Excel integration.
- [Module roadmap](roadmap.md) maps chatbot versus tooling/evaluation ownership,
  dependencies, current status, and milestone checks.
- [Project scope](project.md) records the sponsor brief and implementation boundary.
- [Working context](context.md) records verified status and decisions still pending.

The active milestone is company-context tooling and evaluation. Workbook-aware
research is next; the eventual product interface is an Excel add-in. Browser UI,
workbook operations, and approved exports are deferred.

## Try it without credentials

Requires Python 3.11+ and uv on macOS or Linux. Run from this repository:

```sh
uv sync --locked
uv run python -m provenance demo
```

This is a **scripted offline replay**, not live inference or an accuracy result.
It exercises the same loop as live mode: search → read Apple evidence → return
FY2024 revenue with a citation. It makes no network calls and costs $0.
The JSON output includes the answer, metrics, and complete event trace.

To explicitly authorize saving logs:

```sh
uv run python -m provenance demo --log-dir runs
```

Each run gets a unique directory containing incremental `trace.jsonl` and a
final `result.json`. Without `--log-dir`, output goes to stdout and the harness
does not write files. The model has no file-writing capability. Logs are ignored
by Git; they contain prompts, public excerpts, and responses, but no API keys.

## Evaluation

```sh
uv run python -m provenance validate
```

The dataset has 10 development and 15 heldout tasks across Apple, Microsoft,
NVIDIA, Amazon, and Meta. Three tasks explicitly require abstention. Sources are
small, curated historical extracts of official releases, with URLs, dates,
original section labels, local line locators, and SHA256 checksums.

- [Tasks and answer keys](eval/tasks.json)
- [Scoring rubric, split discipline, and limitations](eval/README.md)
- [Source manifest](data/corpus/sources.json)

The dataset tests extraction, guidance, and comparisons. It does not yet test
full filing navigation or produce a spreadsheet. Gold answers and rubrics are
never passed to the model or retrieval tools. Development task runs restrict
retrieval to their declared sources; `--web` cannot be combined with `--task`.
Heldout tasks are excluded from the run command and have not been evaluated.

Mechanically check a saved development run, substituting its actual run ID:

```sh
uv run python -m provenance grade --task dev-01 --result runs/RUN_ID/result.json
```

This replays the recorded local read-only tools to check evidence/trace
consistency, revalidates citation quotes, and checks values, units, periods, and
source-locator overlap. Logs are not cryptographically authenticated. Human review is
still required for metric identity, citation entailment, arithmetic, unsupported
extra claims, and abstention reasoning. A replay passing these checks is only a
test of the plumbing. It is not a model pass rate. Claim keys are descriptive;
the pre-grader matches on values/units/periods/evidence, not exact key spelling.

## Full company documents

[Cloudflare source packet](source-packet.md) includes the release, 10-Q, 18-page
call transcript, and 116-page investor deck. Originals and extracted content are
hash-pinned. Native parsing preserves page/section references and table-cell
separators; it does not verify chart semantics, OCR, or complete table geometry.

```sh
uv run python -m provenance.evaluation --corpus data/cloudflare-2024-q3 \
  --benchmark eval/company_tasks.json
```

This separate nine-task development suite reports extraction anchors and bounded
retrieval coverage. It is not a model-accuracy score. See [evaluation notes](eval/README.md).

## Checkpointed research

SQLite persists research state at node boundaries. To demonstrate without a key:

```sh
uv run python -m provenance demo --checkpoint /tmp/prov-demo.sqlite \
  --thread-id first --pause-after-tools
uv run python -m provenance demo --checkpoint /tmp/prov-demo.sqlite \
  --thread-id first --resume
```

Only explicit tool-boundary pauses resume automatically. A durable pre-request
marker detects a process death during a provider attempt and blocks duplicate
execution pending billing review. Completed threads return their cached result.
Resume checks question, model, pricing, limits, and corpus identity. SQLite is a
local development backend; server concurrency and production storage are later.

## Live OpenRouter research

Install the locked environment first:

```sh
uv sync --locked
```

Export settings from [.env.example](.env.example), including an OpenRouter key,
model ID, and verified input/output rates. The CLI does not load `.env` files.
The configured model is `deepseek/deepseek-v4.1-flash-1017`. Published prices vary
by schedule; the example uses the maximum published input/output rates checked
on 2026-11-07. Existing environment credentials never trigger calls automatically.

Live calls require `--live` and an explicit budget. LangGraph is the default
runtime; the custom loop and direct OpenAI adapter remain comparison options.

```sh
uv run python -m provenance run --live --task dev-01 --budget-usd 0.05 --log-dir runs
```

The approved development experiment has a **$0.50 aggregate cap**, within the
user-configured $1 daily account limit. A per-run flag alone does not impose a
cross-run daily budget: retain a shared experiment ledger when running a batch.

For exploratory public-web research, additionally export `EXA_API_KEY` and
`EXA_MAX_REQUEST_USD` (a conservative per-request charge under your plan), then:

```sh
uv run python -m provenance run --live --web --budget-usd 0.50 \
  --question "What revenue did Microsoft report for FY2025 Q1?" --log-dir runs
```

Without `--web`, live inference searches only the frozen local corpus. With it,
search also calls Exa; retrieved web pages use stable line numbers within each
run. Live pages are not historical snapshots. Exa integration is contract-tested
only, and an Exa key is not currently configured.

Default limits are 8 model calls, 10 tool calls, 90 seconds total, 30 seconds per
request timeout, and 4,000 maximum output tokens per model call in the CLI.
CLI options can change call counts, total time, and output tokens. SDK automatic
retries are disabled; the legacy HTTP adapter also disables redirects. Deadline
enforcement uses POSIX signals in the CLI's main thread.

Spending is **an application-side estimate, not a guaranteed provider billing
cap**. Before each model call the harness reserves a conservative input estimate
(serialized UTF-8 bytes plus protocol allowance) and maximum output cost using
configured prices. Successful calls settle against reported token counts at
those rates; caching discounts are deliberately ignored. Exa reserves its
configured per-request maximum. Missing billing data, failed calls, and timeouts
retain the full reservation and flag uncertainty. An actual charge above a
reservation stops the run. Configure account-side controls separately if needed.

## Measured development status

[Implementation and live report](eval/reports/live-acceptance.md) records all
28 paid development runs, earlier failures, source versions, limitations, and
**$0.3498927** total conservative token-rate accounting under the $0.50 approval.
All **79 tests** pass. Nine-task BM25 execution completed five answers; a subsequent
four-case final-synthesis check completed all four previously stopped cases.
These separate tuned iterations do not form an independent nine-task pass rate.

Model context retains at most 32K serialized tool-result characters, with whole
older results omitted rather than rewritten. Complete evidence remains in traces
and citation state. LangGraph offers one bounded citation-repair attempt and
reserves the last permitted model turn for a tool-disabled final answer or
abstention. This improves completion without increasing execution limits.

Literal quote checks still do not enforce semantic support, source-specific
instructions, or financial-number coverage in answer prose. Native chart/table
interpretation and OCR comparisons remain unverified. See the report before
interpreting mechanical grades as research accuracy.

An explicitly paid company question uses the selected packet:

```sh
uv run python -m provenance run --live --corpus data/cloudflare-2024-q3 \
  --question "What did Cloudflare guide for Q4 2024 revenue?" \
  --budget-usd 0.05 --log-dir runs
```

For a reproducible paid development batch, export credentials and verified rates,
then use a **new** output directory:

```sh
uv run python -m provenance.experiment --live --corpus data/cloudflare-2024-q3 \
  --benchmark eval/company_tasks.json --tasks packet-01 packet-04 packet-08 \
  --budget-usd 0.10 --per-task-usd 0.03 --output runs/my-development-experiment
```

That ledger caps one experiment. Deduct earlier experiments from any shared
approval/account budget before invoking another. Full public run reports are
versioned under `eval/reports/live`; default diagnostic `runs/` remain ignored.

## Development checks

`uv sync --locked` installs SDKs, the PDF parser, SQLite checkpoint support, and
pinned Ruff. Yarn commands follow this repository's working conventions:

```sh
yarn lint
yarn test
```

Python-only test equivalent: `uv run python -m unittest discover -s tests -v`.
Tests cover control flow, limits, citation checks, malformed calls, provider
failures, cost accounting, frozen-source integrity, and a network-disabled demo.

## Design references

- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangChain agents](https://docs.langchain.com/oss/python/langchain/agents)
- [OpenRouter models](https://openrouter.ai/api/v1/models)
- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling#handling-function-calls)
- [Exa search](https://exa.ai/docs/reference/search) and [contents](https://exa.ai/docs/reference/get-contents)
- [Project brief](https://claude.ai/artifact/3cSNqEgPBvGGNVjAj2vjcH)

[project.md](project.md) records scope and acceptance criteria;
[context.md](context.md) records current verification and remaining work.
