# Provenance finance agent — steps 1–2

A small, read-only finance research harness and a 25-task public-data evaluation.
The model chooses between `search` and `read_source`; deterministic code controls
tool access, call counts, time, and spending reservations. No workflow router,
spreadsheet writer, Python-execution tool, or multi-agent runtime is included.

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

Current priority (2026-11-07): company-context research and evaluation. Workbook
capabilities and UI remain later work; the eventual interface is an Excel add-in.
LangChain/OpenRouter adapter and LangGraph model/tool/finalize execution are now
implemented; offline graph integration passes, while live provider acceptance
remains unverified. The legacy offline path remains
runnable without those dependencies. Page-text ingestion and passage search have
offline tests; raw PDF/OCR extraction is not implemented. See
[ingestion.md](ingestion.md) and [source-packet.md](source-packet.md).

## Research runtime migration

Research dependencies are installed and locked in `pyproject.toml`/`uv.lock`.
Use the project virtual environment so graph integration tests actually run:

```sh
uv sync
uv run python -m unittest discover -s tests -v
uv run python -m provenance demo --runtime langgraph
```

All 44 tests pass, including graph replay and limit checks. The graph demo remains
a scripted replay, not model-quality evidence. OpenRouter model/rates are locally
configured; the CLI still requires exported variables and does not load `.env`
automatically. The selected development model is `deepseek/deepseek-v4.1-flash-1017`.
Accounting retains provisional estimates of $0.40 input / $1.60 output per million
tokens; actual OpenRouter prices vary by provider and need route verification. The user reports
a $1/day OpenRouter limit; this has not been independently verified. Use
`--budget-usd 0.10` for initial development runs. Application budgets are per-run
estimates, not a cross-run daily cap. Live provider acceptance remains pending.

Graph state has explicit messages, response, and answer boundaries. Durable
checkpoints/resumption remain disabled until budget reservations and evidence-read
permissions can be persisted together. Deadlines still use the main-thread POSIX
implementation; server execution is not supported yet.

## Try it without credentials

Requires Python 3.11+ on macOS or Linux. Run from this repository:

```sh
python3 -m provenance demo
```

This is a **scripted offline replay**, not live inference or an accuracy result.
It exercises the same loop as live mode: search → read Apple evidence → return
FY2024 revenue with a citation. It makes no network calls and costs $0.
The JSON output includes the answer, metrics, and complete event trace.

To explicitly authorize saving logs:

```sh
python3 -m provenance demo --log-dir runs
```

Each run gets a unique directory containing incremental `trace.jsonl` and a
final `result.json`. Without `--log-dir`, output goes to stdout and the harness
does not write files. The model has no file-writing capability. Logs are ignored
by Git; they contain prompts, public excerpts, and responses, but no API keys.

## Evaluation

```sh
python3 -m provenance validate
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
python3 -m provenance grade --task dev-01 --result runs/RUN_ID/result.json
```

This replays the recorded local read-only tools to check evidence/trace
consistency, revalidates citation quotes, and checks values, units, periods, and
source-locator overlap. Logs are not cryptographically authenticated. Human review is
still required for metric identity, citation entailment, arithmetic, unsupported
extra claims, and abstention reasoning. A replay passing these checks is only a
test of the plumbing. It is not a model pass rate. Claim keys are descriptive;
the pre-grader matches on values/units/periods/evidence, not exact key spelling.

## Live model mode — configuration deferred

The intended live path defaults to OpenRouter through LangChain and LangGraph.
Exact model and rates remain explicit configuration. No live provider acceptance
test or paid model evaluation has been run. Legacy direct OpenAI remains available
with `--provider openai --runtime custom`.

When ready, export the settings shown in [.env.example](.env.example):
`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_INPUT_USD_PER_MILLION`, and
`OPENROUTER_OUTPUT_USD_PER_MILLION`. Use verified current prices for the selected
model. The CLI does not load `.env` automatically and has no default paid model.
The existing environment key alone never triggers a call.

```sh
uv run --no-sync python -m provenance run --live --task dev-01 --budget-usd 0.50 --log-dir runs
```

For exploratory public-web research, additionally export `EXA_API_KEY` and
`EXA_MAX_REQUEST_USD` (a conservative per-request charge under your plan), then:

```sh
uv run --no-sync python -m provenance run --live --web --budget-usd 0.50 \
  --question "What revenue did Microsoft report for FY2025 Q1?" --log-dir runs
```

Without `--web`, live inference searches only the frozen local corpus. With it,
search also calls Exa; retrieved web pages use stable line numbers within each
run. Live pages are not historical snapshots. Exa integration is contract-tested
only, and an Exa key is not currently configured.

Default limits are 8 model calls, 10 tool calls, 90 seconds total, 30 seconds per
HTTP socket timeout, and 1,600 maximum output tokens per model call. CLI options can
change call counts and total time. API redirects and automatic retries are
disabled. Deadline enforcement uses POSIX signals in the CLI's main thread.

Spending is **an application-side estimate, not a guaranteed provider billing
cap**. Before each model call the harness reserves a conservative input estimate
(serialized UTF-8 bytes plus protocol allowance) and maximum output cost using
configured prices. Successful calls settle against reported token counts at
those rates; caching discounts are deliberately ignored. Exa reserves its
configured per-request maximum. Missing billing data, failed calls, and timeouts
retain the full reservation and flag uncertainty. An actual charge above a
reservation stops the run. Configure account-side controls separately if needed.

## Development checks

The legacy offline runtime uses only Python's standard library. Research SDKs
are installed through the locked project environment. `uv` installs pinned Ruff for lint;
Yarn commands follow this repository's working conventions:

```sh
yarn lint
yarn test
```

Python-only test equivalent: `python3 -m unittest discover -s tests -v`.
Tests cover control flow, limits, citation checks, malformed calls, provider
failures, cost accounting, frozen-source integrity, and a network-disabled demo.

## Design references

- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling#handling-function-calls)
- [Exa search](https://exa.ai/docs/reference/search) and [contents](https://exa.ai/docs/reference/get-contents)
- [Project brief](https://claude.ai/artifact/3cSNqEgPBvGGNVjAj2vjcH)

[project.md](project.md) records scope and acceptance criteria;
[context.md](context.md) records current verification and remaining work.
