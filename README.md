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

- [Browser workbook milestone](docs/web-workbook-spec.md) defines the implemented
  input-review workflow and its boundary before formula editing or live Excel.

- [Excel financial agent research](docs/excel-agent-research-2026-11-18.md) compares
  current products, platform constraints, and proposed live-Excel workflows.
  Research is complete for an initial planning discussion; implementation choices
  remain open.
- [Harness improvement specification](harness-improvement-spec.md) defines the
  next implementation contracts, acceptance gates, and benchmark-driven improvement
  cycle. It is a proposed target; runtime defaults remain unchanged.
- [Product specification](spec.md) covers the research workflow, company-data
  proposal, module contracts, evaluation, web MVP, and later live Excel integration.
- [Module roadmap](roadmap.md) maps chatbot versus tooling/evaluation ownership,
  dependencies, current status, and milestone checks.
- [Project scope](project.md) records the sponsor brief and implementation boundary.
- [Working context](context.md) records verified status and decisions still pending.
- [Finance accuracy benchmark plan](eval/benchmark-plan.md) records the selected
  datasets, scoring, test conditions, and future implementation stages.

The active milestone is company-context tooling and evaluation. Finance accuracy
benchmarking is active: [external benchmark preparation and scoring](eval/external-benchmarks.md)
now support FinEval, FinQA, FinanceBench, TAT-QA, and ConvFinQA. Two small
preregistered public development pilots are complete; annotation concerns remain
separate from automatic scores. The product includes a sideloadable Office.js Excel add-in.

The research app and Excel task pane use live Exa search with cited source reads,
follow-up questions, and workbook context. See [Excel setup](office/README.md).

## Web app

Requires Python 3.11+, uv, and Node 20+. From the repository root:

```sh
corepack yarn web          # install web deps, build, serve http://127.0.0.1:8765
```

Live answers need an OpenRouter key in a local, gitignored `.env` (the server
loads it at startup; never commit it):

```sh
OPENROUTER_API_KEY=...
EXA_API_KEY=...
```

Model choice, accounting rates, and spend limits live in `research.config.json`.
The web launcher loads this config at startup; restart after changing it.
Live research requires both provider keys and valid config.
Missing configuration disables research. There is no replay or sample-data fallback.

What you can do:

1. Open the app or Excel task pane to research live web sources with Exa.
2. Ask a question and watch searches, reads, model steps, and running cost stream
   into the Activity tab.
3. Click any source tag in the answer to open the exact cited lines, with the quote
   highlighted, the original page or section, the archived original, and the public URL.
4. Ask follow-ups. The last three turns (questions, answers, cited locators) are
   carried as explicit context; the agent must re-read evidence before citing it.
5. Upload an `.xlsx`, select a range, and attach
   it to the next question. Use Go to range or paging to navigate beyond the first
   preview; inspect saved values, formulas and calculation status. Answers can cite
   workbook cells.
6. When asked, the agent proposes ordinary input-value edits with citations. Nothing is written
   until you approve; approval creates a separate copy with a source comment on
   each changed cell and a `Provenance log` sheet. The saved copy is reopened to
   verify changes and preserved formulas; Excel recalculation is requested on open.
   Calculation remains pending in the browser. Re-upload the copy to review a new version.

The workbook milestone supports `.xlsx` up to 5 MB compressed, 25 MB expanded,
and 30 worksheets. Formula, merged, table, protected and hidden-sheet targets are
read-only; fidelity-risk features such as charts, images, pivots and external links
block edited-copy export. Original files remain unchanged. Sessions are in memory
and do not survive server restart. See the [spec](docs/web-workbook-spec.md) for
acceptance checks and later milestones.

Limits per question: 8 model steps, 10 tool calls, 120 s, and `max_turn_usd` in `research.config.json` (default $0.10). Live spend is
recorded in `runs/web/cost-log.jsonl` and capped at `total_spend_usd` (default
$1.00); set `WEB_LEDGER` to use a separate ledger. Each turn
runs in its own worker process (the runtime's deadlines need a main thread), and
traces are written to `runs/web/traces/`.

Tests: `corepack yarn test` covers the web backend (workbook snapshots and export,
workbook tools and citations, ledger, worker, API). `corepack yarn web:e2e` runs the
live API interface with deterministic provider and Office host fixtures in Playwright.
On a fresh checkout, install the test browser first with
`npx --prefix web playwright install chromium` after installing web dependencies.

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

H3's opt-in backend [typed read session](eval/assessments/typed-read-authorization-v1/report.md)
binds source authorization and cutoff, records actual FactReader responses and
verifies reconstruction/replay. Completed delivery does not establish financial
semantics or model visibility; calculator and answer-v2 integration remain pending.

The [model/effort comparison runner](eval/assessments/model-effort-v1/infrastructure-report.md)
now supports explicit effort, pinned providers, durable accounting and interleaved
tool-free trials. The [first pilot protocol](eval/assessments/model-effort-v1/pilot-protocol.md)
freezes three supplied-evidence cases across two models at low/high effort, plus
one unresolved-reference exclusion without replacement. Infrastructure acceptance
is not an accuracy result or a model recommendation. The
[first live pilot](eval/assessments/model-effort-v1/pilot-report.md) stopped on its
first transport failure with unknown billing; no successful outputs or model
ranking resulted.
Comparison failures now retain only recognized transport messages/HTTP statuses
for diagnosis. Arbitrary exception text remains stripped, and unknown billing
still stops all remaining calls without retrying.
The [one frozen follow-up](eval/assessments/model-effort-v1/followup-report.md)
returned HTTP 404 on its first request and stopped. Neither pilot produced
completed answers; public model listings do not establish live compatibility.

H2's [calculation infrastructure](eval/assessments/evidence-calculations-v1/report.md)
provides bounded Decimal arithmetic, trusted-evidence references, financial
compatibility checks and full replay. It is not yet a model-facing tool: H3 must
provide actual source admission, complete model-visible support and budget
integration first. Existing agent tools and defaults remain unchanged.

The opt-in `--runtime-profile trace-receipts-v1` is available on
`run --engine langgraph --provider openrouter`. It records the projected messages
and mapped application request before dispatch, including failed requests, and
binds checkpoint v3 to instructions, tools, configuration, and source metadata.
Use `--log-dir` to retain the trace. Receipt verification rebuilds the request
locally; it does not attest provider wire bytes, model attention, or financial
correctness. Legacy runs remain the default, and checkpoint profiles cannot be
converted on resume. See the [H1 acceptance report](eval/assessments/model-input-receipts-v1/report.md).

External benchmark pilots (2026-11-16): [core pilot](eval/reports/external-pilot-2026-11-16/report.md)
and [table/conversation pilot](eval/reports/expansion-pilot-2026-11-16/report.md).
The latter records TAT-QA 4/4 official matches and ConvFinQA 6/9 turns, 0/2 whole
conversations in both history conditions. Small-sample, public-data and annotation
limitations prevent broad accuracy claims. Total recorded conservative spending
across development is $0.4814193. The original holdout remains unrun.

[A frozen DPO component-search experiment](eval/reports/dpo-retrieval-2026-11-16/report.md)
used more searches without improving page coverage; it was not promoted. An
[equal-budget statement-context variant](eval/reports/statement-context-2026-11-16/report.md)
also failed to improve final coverage and lost a required candidate page.

[Evidence-component diagnostics](eval/reports/evidence-components-2026-11-16/report.md)
show complete annotated evidence in parent passages for 2/3 exposed tasks, but
0/3 in returned snippets across all three retrieval conditions. This measures a
search-to-read gap, not financial answer accuracy.

[Bounded reads](eval/reports/bounded-reading-2026-11-16/report.md) deliver complete
annotated packets for 2/3 tasks after three reads, with all three retrieval policies
tied. All 45 original reads succeeded and replayed exactly. A separate
[context-retention diagnostic](eval/reports/context-retention-2026-11-16/report.md)
finds that the current policy loses those complete packets after five reads
(2/3 before projection, 0/3 retained). This is not measured answer accuracy; agent
defaults are unchanged.

A [same-budget retention challenger](eval/reports/context-priority-2026-11-16/report.md)
recovers the two inspected losses by prioritizing earlier optional reads. It remains
experimental: these exposed cases do not justify changing the default policy.

[Broader six-source validation](eval/assessments/financebench-context-v1/progress.md)
now fixes six new development source groups and their pinned PDF inventory before
content inspection. All six bodies are acquired and extracted (981 pages);
all six evidence-location packets are [independently reviewed](eval/assessments/financebench-context-v1/annotation-report.md)
and frozen before retrieval. Three semantic caveats remain explicit; financial
answers are not validated. The [frozen comparison](eval/assessments/financebench-context-v1/comparison-report.md)
finds no challenger improvement: both retain 1/6 complete packets at five reads,
with five blocked projections. Production remains unchanged. Native text quality outside the ten inspected pages
is unverified,
and failed cases will not be replaced with easier ones.

[PDF visual review](eval/reports/pdf-visual-quality-2026-11-16/report.md) distinguishes
retrieval misses from extraction failure and records a fiscal-year reference ambiguity.
All 419 native-text pages replay unchanged with structured page diagnostics.

An opt-in [PDF read-metadata projection](eval/read-extraction-design.md) retains
only returned-page diagnostic entries while preserving global warnings and the
full diagnostics hash/reference. The [frozen assessment](eval/assessments/financebench-compact-read-v1/report.md)
removes all blocked projections and cuts read-response characters 76.05%, with
evidence unchanged. Complete coverage remains 1/6 at five reads; retrieval gaps
persist, and frozen locations are not exhaustive semantic judgments. Full metadata
remains the default. Both `demo` and `run` accept
`--read-extraction-version pdf-returned-pages-v1`; the mode is recorded in traces,
respected by grading, and must match on checkpoint resume.

A [page-context ranking prototype](eval/retrieval-research-2026-11-16.md) passes
synthetic checks while preserving default search responses. Its [assessment runner](eval/assessments/financebench-page-ranking-v1/progress.md)
verifies whole-run replay before labels. The [frozen comparison](eval/assessments/financebench-page-ranking-v1/report.md)
regressed from 1/6 to 0/6 at five reads, so the challenger is not promoted.
A [saved-pool diagnosis](eval/assessments/financebench-page-ranking-v1/pool-diagnosis.md)
separates two cases with short label-assisted window witnesses from four whose
pools lack frozen locations; it is an evaluator diagnostic, not a retrieval policy. A [metadata-only validation reservation](eval/assessments/financebench-page-validation-v1/progress.md)
keeps six slots closed; Amazon and Microsoft have prior issuer exposure and remain
explicitly flagged without replacement. The separate [annotation-validity research](eval/incomplete-judgments-research-2026-11-16.md)
supports a [staged blinded audit](eval/assessments/financebench-evidence-audit-v1/progress.md)
that has completed and locked independent question-only interpretation and reconciliation
before evidence or outcomes are shown. Six cases retain 16 explicit interpretations;
two independent evidence reviews and fresh all-case adjudication are now locked
with 60 requirements and five complete sets across interpretations. Mechanical
checks verify 223 citation occurrences; financial validity is not independently
established. A separately frozen read-attribution diagnostic finds no accepted set fully covered
by either branch; only two cases have adjudicated sets, so this is not a six-case
retrieval-failure rate. Independent reproduction passed. Frozen scores remain unchanged.

A [context-markup inventory](eval/reports/context-markup-2026-11-16/report.md)
finds no explicit HTML header links in four exposed sources, but numeric Inline
XBRL tags in three filings. This prioritizes a typed-context extraction investigation;
lexical tags are not validated facts. The v3 release-page rejection is retained.
A separate [Arelle negative preflight](eval/spikes/arelle/README.md) verifies that
missing schemas must reject facts even when its API reports success. Successful
issuer extraction remains pending. A separate [five-fact synthetic acceptance
fixture](eval/spikes/arelle/typed-values-report.md) verifies typed values and source-cell
ancestry; rendered visibility and broader fact types remain unverified. A separate
[guarded version](eval/spikes/arelle/guarded-values-report.md) rejects a discovered
timezone mismatch and preserves duplicate conflicts; 15 optional tests pass. A
[controlled 2.47.5 comparison](eval/spikes/arelle/candidate-comparison-report.md)
reproduces those synthetic behaviors while holding other package versions fixed.
A [dimensional scope fixture](eval/spikes/arelle/dimensions/README.md) additionally
preserves explicit/typed members and residual scenario content; six optional tests
pass. A separate [14-case applicability matrix](eval/spikes/arelle/applicability/README.md)
now distinguishes usable defaults, domain membership and closed-cube container scope;
seven additional tests pass. Integration into a general adapter remains pending.
A [real-filing offline load](eval/reports/xbrl-dependencies-2026-11-16/report.md) now
uses 24 acquired dependencies for the existing ODFL June filing. The subsequent
[pinned SEC transform comparison](eval/spikes/arelle/sec-transforms-report.md) resolves
its twelve transformation failures while preserving the other 492 records. All 504
facts pass schema validation; general financial evidence acceptance remains unverified.
The dependency inventory/acquisition path adds 13 core regression tests.
The [source-occurrence sidecar](eval/reports/xbrl-occurrences-2026-11-16/report.md)
accounts for all 504 facts, including 420 exact cell joins and explicit outside-table/
hidden dispositions. Source locations are bound to the validated runtime; rendered
visibility and general financial evidence acceptance remain unverified.


The [experimental typed fact export](eval/reports/xbrl-facts-2026-11-16/report.md)
now integrates all 504 exposed ODFL facts with 71 contexts, five units, separate
provenance-bound taxonomy defaults and rebuilt source geometry. Exact numeric and
partial-date representations pass independent source expectations. Seven optional
checks and 431 core tests pass; financial acceptance and rendered visibility remain
unverified. No default policy or reserved evaluation source changes.

The [typed-fact delivery diagnostic](eval/assessments/xbrl-evidence-delivery-v1/protocol.md)
now measures existing table reads with exact row locations: 139 reads return all
420 mapped fact occurrences across 412 cells; 84 facts have no mapped cell. This
is an exposed-source, location-assisted coverage check, not retrieval or answer
accuracy. The [opt-in exact-ID reader](eval/reports/xbrl-reader-2026-11-16/report.md) now
reconstructs every occurrence within bounded responses: 484 immediate and 20
deferred. Final case manifests and prospective question assessment remain pending.

Source ingestion now includes an independent native HTML geometry sidecar,
FinanceBench whole-document assembly, and bounded page-level PDF diagnostics. New HTML corpora can explicitly select
`--html-text-version native-html-text-v2` to suppress explicit hidden content and
preserve text boundaries; legacy extraction remains the default for replay.
A standalone opt-in [table sidecar v3](eval/reports/table-template-2026-11-16/report.md)
also isolates inert templates. Tools and assessment protocol v4 support explicit
sidecar selection; defaults retain v2, and a real assessment requires a new freeze.
[Extraction findings](eval/reports/source-ingestion-2026-11-16/report.md) and
[connected table-evidence protocol](eval/table-evidence-protocol.md) distinguish
structure, retrieval, and financial meaning. The [raw table tool probe](eval/reports/table-runtime-2026-11-16/report.md)
measures 4/4 explicit-window controls and 2/4 question-search context coverage,
without claiming semantic answer success. A separately frozen soft-prefix
weighting experiment stayed at 2/4 and was not promoted. Full-agent FinanceBench inference
remains disabled pending source-quality acceptance. A separate
[locked assessment runner](eval/table-runtime-design.md) now keeps annotation files
out of retrieval execution, with separate receipt-bound replay grading. Broader
cohort acquisition and annotation remain incomplete: a frozen issuer-delivery
attempt verified 2/6 copies, with all four failures retained. See
[assessment progress](eval/assessments/native-html-v1/progress.md). Versioned publication-cutoff
controls now enforce conservative source eligibility and are scored separately.

Latest frozen company-research evaluation (2026-11-07): six new public development questions,
**5/6 completed**, **2/6 unchanged mechanical passes**, and **4/6 evidence-supported
task passes under coding-agent review**. Two numerical answers are substantively
correct but fail exact period formatting; a search-only abstention lacks a source
read, and one task stops during citation repair for spending-reservation headroom.
A supported extra figure in one otherwise passing answer lacks a structured claim.
These are small, single-company development results, not general accuracy or human
financial validation. See the [full report](eval/reports/frozen-evaluation-2026-11-07/report.md)
for preregistration, all failures, complete traces, and offline reproduction.
Fresh estimated cost: $0.0863112; combined with cloud development: $0.4362039.

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

To run without application spending caps, replace `--budget-usd` and
`--per-task-usd` with `--no-spend-limit`. Single-question `run` also accepts
`--no-spend-limit` instead of `--budget-usd`. Cost tracking, time/tool limits,
and stops for uncertain billing remain active. Interrupted uncapped tasks have
unknown cost until reviewed; they have no finite task reservation.

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

`yarn test` runs the full suite with compact progress and detailed failures.
During editing, use a focused subset such as `yarn test -k workbook` or
`yarn test -p 'test_calculation*.py'`; run the full suite before a PR.
Add `-v` when individual passing test names are useful.

Python-only test equivalent:
`uv run --extra benchmark-metrics python -m unittest discover -s tests`.
Tests cover control flow, limits, citation checks, malformed calls, provider
failures, cost accounting, frozen-source integrity, and a network-disabled demo.
The suite also covers evaluation tooling and the web app. Keep tests for distinct
behavior or regressions; avoid adding tests solely for trivial implementation
details or duplicating an existing scenario.

## Design references

- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangChain agents](https://docs.langchain.com/oss/python/langchain/agents)
- [OpenRouter models](https://openrouter.ai/api/v1/models)
- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling#handling-function-calls)
- [Exa search](https://exa.ai/docs/reference/search) and [contents](https://exa.ai/docs/reference/get-contents)
- [Project brief](https://claude.ai/artifact/3cSNqEgPBvGGNVjAj2vjcH)

[project.md](project.md) records scope and acceptance criteria;
[context.md](context.md) records current verification and remaining work.

## Excel Office.js integration (2026-11-20)

A sideloadable task pane now attaches selected Excel cells to research questions
and inserts cited claims into new worksheets. See [setup and limitations](office/README.md).
Live cell proposal application and continuous synchronization are not implemented;
real Excel host verification remains pending.

## Daloopa quick/full benchmarking

The [navigation improvement loop](eval/document-navigation-loop-2026-11-23.md)
adds versioned document ingestion and finding. Use `--navigation document-v2` for
the selected pilot treatment; `baseline` remains available for comparisons.
[Measured quick results](eval/reports/navigation-loop-2026-11-23/quick-results.md)
improve numerical coverage. Full-suite verification resumed after a provider
allowance interruption; no full-suite improvement is yet established.

The [Daloopa benchmark guide](eval/daloopa-benchmark.md) adds a fixed 25-question
quick mode and preserves the full 500-question inventory alongside the existing
suite. After preparation, `yarn benchmark` and `yarn benchmark:full` show plans;
paid execution requires `--live` plus document access. Numerical matching and
source-supported correctness are reported separately.

Token rates estimate costs; they do not set spending limits. Edit
`research.config.json`: `model`, `input_usd_per_million`,
`output_usd_per_million`, `exa_max_request_usd`, `max_turn_usd`, and
`total_spend_usd`. Rates remain the user-supplied 0.40/1.60 accounting estimates;
automatic provider-price discovery is not implemented. The Excel/web launcher
bridges this config into the existing worker environment internally, overriding
stale non-secret environment values. Benchmark CLI configuration is unchanged.

Credential loading correction (2026-11-23): local `.env` values override stale
inherited variables. Direct authentication with the file key returned HTTP 200;
the earlier 401 reports came from a different inherited key, not the file key.
