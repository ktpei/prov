# Project scope

## Broader context validation result — 2026-11-16

[Six new development source groups](eval/assessments/financebench-context-v1/progress.md)
are frozen before content inspection: Verizon, Coca-Cola, Costco, Johnson & Johnson,
3M and American Water Works. Independent metadata review confirms existing seed-17
development membership, six distinct companies and no known exposed-company overlap.
All six pinned PDF bodies are acquired and byte-verified with zero failures or
retries. Frozen preparation/native extraction is complete (981 pages, 34,904 lines);
[Outcome-blind annotation](eval/assessments/financebench-context-v1/annotation-report.md)
and independent review are complete for all six cases across ten referenced pages.
Packets preserve ambiguities in 3M, Coca-Cola and Verizon; mapped locations are not
validated financial answers. [Frozen comparison](eval/assessments/financebench-context-v1/comparison-report.md)
now retains complete packets for 0/6, 0/6 and 1/6 at one/three/five reads under
both policies, with 4/6, 5/6 and 5/6 blocked projections. No challenger promotion.
Five other pages lack native text and remain visually unverified. The independently reviewed
[comparison runner](eval/assessments/financebench-context-v1/compare.py) passes
nine synthetic failure/replay tests; six original searches/thirty reads and an exact
replay are complete. [Saved-response diagnosis](eval/assessments/financebench-context-v1/response-size-report.md)
attributes 79.53% of read output characters to extraction metadata. The new opt-in
[returned-page projection](eval/read-extraction-design.md) preserves global warnings
and full-diagnostics provenance while narrowing only response page records.
Independent review and synthetic checks pass. A [controlled assessment wrapper](eval/assessments/financebench-compact-read-v1/progress.md)
verified historical full-mode compatibility and exact replay in both modes. Compact
metadata removed all blocked projections and reduced read output characters
76.05%; complete evidence coverage remained 0/6, 0/6 and 1/6. Operational mode
integration and missing retrieval components are next. Full metadata
remains the default.
All 342 tests and lint pass. Four prior TAT-QA issuer identities remain unresolved, so global cross-suite
issuer disjointness is not claimed. No availability-based replacements are allowed.

## Context-priority challenger — 2026-11-16

[Earlier optional-read preference](eval/reports/context-priority-2026-11-16/report.md)
recovers complete packets for 2/3 cases at five reads, versus 0/3 for the exact
baseline, under the same 32K character limit. NIKE and Ulta improve; Walmart still
fails retrieval. Two wins, zero losses, one tie on exposed development cases; no
default promotion. Fresh validation is required before adoption. All 310 tests
and lint pass, with no paid calls or holdout changes.

## Context-retention result — 2026-11-16

[The original-question context diagnostic](eval/reports/context-retention-2026-11-16/report.md)
retains complete annotated read packets for 1/3, 2/3 and 0/3 tasks at one/three/five
reads, versus delivered coverage of 1/3, 2/3 and 2/3. At five reads the existing
newest-first policy drops early NIKE/Ulta evidence. All snapshots fit the current
32K serialized-output character budget; no policy changed. This is synthetic
context retention, not measured model accuracy. All 304 tests and lint pass.

## Bounded-reading result — 2026-11-16

[The frozen comparison](eval/reports/bounded-reading-2026-11-16/report.md) delivers
complete annotated packets for 1/3 tasks after one read and 2/3 after three/five,
versus 0/3 in search snippets. All three retrieval policies tie. All 45 original
reads succeeded without truncation; 45 separate replay reads verified the traces.
Ulta is complete in one response, NIKE needs a union, and Walmart still misses.
The read result alone establishes neither financial accuracy nor model-visible
context; the separate retention result above finds later evidence loss. This
reading cycle passed 295 tests and lint, with no additional paid spending.

## Evidence-component diagnostics — 2026-11-16

[Replay-bound component coverage](eval/reports/evidence-components-2026-11-16/report.md)
shows the same result for all three saved retrieval conditions: complete annotated
packets in parent passages for 2/3 tasks at top three/five, but 0/3 in returned
snippets. NIKE requires a union of parent passages; Ulta has a complete first
parent. This posthoc development diagnostic separates read opportunities from
text actually returned, without changing page scores or claiming answer accuracy.
All 278 tests and lint pass. Bounded reading is the next evaluation question.

## Broader assessment preparation — 2026-11-16

The [locked native-HTML assessment plan](eval/assessments/native-html-v1/plan.md)
records a metadata-verified six-filing proposal across three new issuers, with 21
positive question slots and three publication-availability controls. The first frozen acquisition attempt returned HTTP 403 for all six sources
(0/6 verified downloads). A separately frozen issuer-delivery attempt verified
2/6 copies (both Old Dominion); Casey’s returned HTTP 403 and Ameren delivered
rendered viewer HTML that remains ineligible. Offline extraction succeeded on the
two copies without a completeness claim. A separately frozen complete-submission
attempt returned four HTTP 403 responses (zero containers); those routes will not
be automatically retried. All six dispositions remain recorded in
[assessment progress](eval/assessments/native-html-v1/progress.md). Questions are not authored. A separate search-only runner
passes synthetic integrity/interruption checks. Separate receipt-bound grading
now validates replay and complete evidence alternatives. Selected-source cutoff
controls now distinguish unavailable, unknown and observed-available artifacts;
full provenance gates and real cohort acquisition remain pending.
Synthetic review found hidden-text and block-boundary defects in legacy HTML text
extraction. An opt-in `native-html-text-v2` repair passes adversarial tests, with
explicit CSS/completeness limitations; legacy replay and frozen corpora remain
unchanged. This is preparation, not a new accuracy result.


## Template extraction repair — 2026-11-16

[Opt-in sidecar v3](eval/reports/table-template-2026-11-16/report.md) isolates inert
HTML templates from visible table geometry and text. Seven new synthetic tests
pass; four v2 sidecars replay exactly. Explicit v3 selection now reaches tools, run-protocol v4 and separate grading;
default tools and historical protocols retain v2. All 36 historical tool responses
replay exactly. A real assessment still requires a new freeze.
This is a standalone extraction repair, not improved financial accuracy.

## Raw table runtime — 2026-11-16

[Fixed offline probe](eval/reports/table-runtime-2026-11-16/report.md): standalone
raw-table reads cover all required cells for 4/4 explicit-window controls, while
original-question search plus one read improves 1/4 → 2/4 after excluding redundant
prefix rows. Correct tables rank first 3/4 and within three 4/4. The raw grader does not infer semantic or typed answer success.
Default graph/citations remain unchanged; no additional paid inference occurred.
A frozen soft-prefix weighting challenger remained 2/4, with no paired wins or
losses. Both earlier versions replay exactly; v2 remains the default. The negative
result is retained, and broader uninspected development assessment is next.


## Statement-context retrieval — 2026-11-16

[Equal-budget context terms](eval/reports/statement-context-2026-11-16/report.md)
left coverage at 2/4 pages and 2/3 complete tasks, while Walmart’s expected
candidate-page coverage fell from 1/2 to 0/2. No promotion. The prior component
policy replays exactly. Passage diagnostics do not support blaming numeric length
or missing main-passage headers for these misses.

## DPO retrieval experiment — 2026-11-16

[Question-only component retrieval](eval/reports/dpo-retrieval-2026-11-16/report.md)
used seven searches versus three but remained at 2/4 annotated pages and 2/3 tasks
with complete page coverage. No paired wins/losses; default unchanged. One missing
Walmart page entered the candidate pool but was discarded, and the other never
entered it. The negative result and exact baseline replay are retained.

## PDF visual quality review — 2026-11-16

[Five rendered pages](eval/reports/pdf-visual-quality-2026-11-16/report.md) distinguish
Walmart retrieval misses from missing text and flag Ulta’s fiscal-year convention.
A ninth content-bound reference issue preserves original gold. Page diagnostics
now expose native-text counts and line ranges; all 419 extracted pages replay
with identical text and locations. No OCR, inference or score changes occurred.

## Source-quality iteration — 2026-11-16

Whole-document diagnostics bind originals, extracted text, and the full manifest.
Three-task retrieval reaches 2/4 annotated pages at five hits; declared-document
scoping improves first-hit recall from 1/4 to 2/4 without fixing the remaining task.
Native HTML v2 fixes explicit-hidden contamination and retains raw headers/captions;
four evaluator-only packets check source/period/sign/scale associations. Lint and
271 tests pass. Full-agent FinanceBench inference and human adjudication remain
pending. [Source findings](eval/reports/source-ingestion-2026-11-16/report.md).


## Expansion pilot — 2026-11-16

[Fixed table/conversation pilot](eval/reports/expansion-pilot-2026-11-16/report.md):
TAT-QA EM/F1/scale 4/4; both ConvFinQA history conditions 6/9 turns and 0/2 whole
conversations. All 22 requests completed; $0.0290532 conservative cost. Remaining
authorization $0.5185807. Source-level review flags annotation/scale ambiguities;
these small public development results are not human-validated financial accuracy.

## Table/conversation expansion — 2026-11-16

All five selected public dataset families now have adapters. TAT-QA uses a pinned
MIT-licensed official metric with explicit numeric-output safeguards; ConvFinQA
has history-isolated projections and per-turn/whole-conversation scoring, with
bounded conversation execution now available. New report-level partitions share FinQA/
ConvFinQA exposure rules. Full imports and 161 tests passed; no new model-quality
claim or spending accompanies this expansion. [Details](eval/external-benchmarks.md).

## External pilot measured — 2026-11-16

[Ten-task development pilot](eval/reports/external-pilot-2026-11-16/report.md):
CFA-Easy 3/3 and CFA-Challenge 2/2 adapted choice passes; FinQA 2/3 adapted scalar
passes with one output-limit failure; FinanceBench two completed oracle responses,
automatic semantic accuracy unset. Independent coding-agent review found an
underspecified FinQA question and FinanceBench denominator/percentage ambiguities.
These are tiny public development diagnostics, not official or human-validated scores.

At that pilot boundary, conservative cost was $0.0161622 and cumulative recorded
estimate $0.4523661. The later expansion pilot above supersedes its remaining budget. No uncertain billing flags or original
holdout calls. Implementation and protocol are published in draft
[PR #2](https://github.com/ktpei/prov/pull/2), not merged. Lint and 112 tests passed.
Earlier no-live-run statements below describe pre-pilot stages.

## Active benchmark loop — 2026-11-16

The user authorized continuous benchmark integration, extensive ingestion research,
and coordinated subagent work. [Workflow](eval/external-benchmarks.md),
[research](eval/external-benchmark-research.md), and [cycle ledger](eval/improvement-loop.md)
record current work. Five dataset families have adapters, hash-pinned preparation,
and bounded execution for tool-free conditions. Two preregistered pilots are
complete. Unresolved annotations are content-bound and retained in the denominator
for later preparations; old scores remain frozen. Source-quality diagnostics and
connected table-evidence acceptance are in progress. No human validation is claimed.


Informal, unpaid, part-time proof of concept for ProvenanceXL. The selected brief
is a single model-directed finance agent with a small tool set and an honest
evaluation. Implemented scope covers the original steps 1 and 2. The 2026-11-04 request
authorizes a product specification and module roadmap for the wider brief.
The 2026-11-07 approval authorizes company-context tooling, LangChain + LangGraph,
OpenRouter integration, and reproducible evaluation. Workbook and UI implementation
remain deferred.

## Benchmark selection — 2026-11-16

The selected next evaluation scope is financial knowledge, numerical reasoning,
report interpretation, supported research, and conversations. Use Salesforce
FinEval, FinQA, FinanceBench, TAT-QA, ConvFinQA, and custom prov tasks as specified
in the [benchmark implementation plan](eval/benchmark-plan.md). Core implementation
starts with FinEval, FinQA, FinanceBench, and custom tasks; Finance Agent Benchmark
is a later challenge. Excel/workbook benchmarking is deferred. The initial planning decision has since been implemented through the five adapters
and two development pilots described above.
The plan records proposed counts, scoring, split discipline, and exit checks.

## Evaluation update — 2026-11-07

A preregistered frozen-runtime batch of six fresh public company-research tasks
returned 5 final answers, 2 unchanged mechanical passes, and 4 evidence-supported
task passes under coding-agent review. All six were attempted once; no tuning or
selective reruns. Original heldout inference remains unrun. Fresh estimated cost
was $0.0863112; combined development estimates total $0.4362039. This small
single-company batch is not a general accuracy or human-validation result.
See the [evaluation report](eval/reports/frozen-evaluation-2026-11-07/report.md)
for formatting false negatives, genuine failures, output-contract defects, and
the next broader evaluation boundary. Runtime behavior was not changed here.

## Sponsor brief and selected direction

Source: [Provenance × Tech@NYU, Fall 2026](https://claude.ai/artifact/3cSNqEgPBvGGNVjAj2vjcH),
read directly on 2026-11-03. The user confirmed that **brief 1 is our project**;
briefs 2 and 3 remain context, not additional implementation commitments.

Provenance is a system of record for financial models and their decks, used
inside Excel and PowerPoint by deal teams at banks and funds. It preserves
versions, explains exact changes and their reasons, and restores prior states.

### Brief 1: finance agent harness — selected

Build “Claude Code for the analyst”: one model-directed loop chooses tools,
observes results, and decides its next action. No keyword routers or scripted
financial workflows. Deterministic code owns safety, budgets, and timeouts.

The full proof of concept calls for 5–7 small tools with clear names and compact
results, covering Exa web search, SEC filings and XBRL, market data, spreadsheet
reading/writing, and Python execution. Any SDK or a custom loop is acceptable.
The evaluation is a 25-task finance set, with examples including a six-company
comps table from filings and management's gross-margin guidance on the last call.

Sponsor acceptance measures: task pass rate, tool-error rate, cost and latency
per task, and whether every numerical claim names its source (URL, filing,
page). Report failures as well as successes. The current two-tool foundation
below is a deliberately limited first stage, not completion of the full brief.

### Brief 2: deal agent — related, not selected

A separate Devin-style team of specialist agents reads a public stand-in data
room: a company's 10-K, latest investor deck, and last earnings transcript.
A planner delegates; a reader indexes page locators; a modeler writes a draft
three-statement or LBO workbook with live formulas; a checker recalculates and
reconciles hardcoded inputs to cited pages; a deck bot produces five slides with
figures traceable to cells. It also produces a diligence request list for gaps.

Its evaluation measures correct page citations for hardcoded inputs,
error-free workbook recalculation, and blind draft review by two finance
students. Every write requires human approval. These requirements inform future
artifact provenance and checking, but do not change our single-model runtime.

### Brief 3: alternatives — reference only

- Slide-to-cell attribution: match every investor-deck figure to a public XBRL
  source line; measure precision and recall. The sponsor marks this recommended
  and describes it as its hardest problem.
- Spreadsheet error benchmark: public models with seeded sign flips, off-by-one
  ranges, hardcodes in formula rows, and hidden circularity; a scorer and results
  from three frontier models.
- Model change narrator: explain changes between workbook versions in analyst
  language and score against human-written notes.
- Excel-to-code round trip: compile a model to a Python dependency graph and back
  to Excel; prove value equivalence through LibreOffice recalculation.

### Shared ground rules and semester deliverables

- Public data only: filings, investor decks, and transcripts; no private deal
  files, sponsor codebase, or sponsor cloud access.
- Any LLM provider is acceptable; maintain a cost log.
- Evaluation precedes the demo; quantitative results are required.
- Agents propose; humans approve anything that writes a file. This is a product
  requirement, not a request for confirmation on already-authorized repo edits.
- Deliver a repo runnable with one command, a 3-minute demo video, and a 1-page
  write-up covering measurements, failures, and cost per task.
- Sponsor check-in at week 6 and final review at semester end; calendar dates
  have not been established here.

## Step 1: evaluation foundation

- Fix three useful task types: financial extraction, management guidance, and
  cross-company comparison; include evidence-limited abstention cases.
- Use five public companies, explicitly dated documents, and original source
  URLs. Keep local excerpts small and distinguish them from full filings.
- Create 25 questions, each with an expected answer, source locators, units,
  periods, tolerances, and rubric: 10 dev and 15 heldout.
- Validate source hashes, split counts, references, and locator bounds.
- Keep expected answers out of model context and retrieval.

These artifacts are implemented. The initial holdout shares companies and
documents with development tasks, so it is not an independent generalization
benchmark. Numerical gold facts were researched against official releases;
derived answers were checked arithmetically. No model-quality result is claimed.

## Step 2: minimal agent loop

- One model selects tools, sees their results/errors, and chooses its next step.
- Start with `search` and `read_source`; no financial workflow routing.
- Enforce model/tool call limits, a wall-clock deadline, bounded HTTP, and
  conservative cost reservations; record stops and failures explicitly.
- Return structured claims with evidence locators and matching quotes.
- Produce complete model/tool event logs plus cost and elapsed time.
- Verify the loop offline and provide an opt-in live OpenAI adapter.

Implemented with a labeled offline replay and fake-HTTP contract tests. Live
acceptance remains deferred at the user's request. Quote presence proves
retrievability, not that the evidence logically supports a claim.

## Explicitly later

XBRL normalization, financial-calculation tools, market data, workbook
reading/writing and approval UI, full benchmark execution, model/prompt tuning,
deployment, a production UI, and a production financial research service.

## Decisions — current as of 2026-11-07

- Python 3.11+ backend; LangChain model adapter and LangGraph runtime.
- OpenRouter model `deepseek/deepseek-v4.1-flash-1017`; $0.50 aggregate live
  acceptance budget within a $1 daily account limit. Credentials stay out of Git.
- Company-context tooling first: full Cloudflare 2024 sources, passage search,
  bounded evidence reads, numerical and qualitative claims, independent evaluation.
- Original documents/version hashes are authoritative. Extracted blocks preserve
  page/section identity. Stored evidence, workflow state, and model context differ.
- Native extraction is the baseline. Docling and Unlimited-OCR are replaceable
  candidates; adoption requires verified accuracy and feasible execution.
- One research agent. Development subagents are explicitly authorized for this run
  and do not change the product into a specialist-agent architecture.
- Keep old custom loop and 25-task corpus as regression baselines; heldout tasks
  remain separate from development and are not run without authorization.
- Browser chatbot, workbook reading/writing/export, and ownership allocation deferred.
  Finance accuracy benchmarking takes priority; eventual interface is an Office.js Excel add-in.
- Frozen local packets require no Exa key. Live web discovery is optional/later.
- Backend file writes are deterministic diagnostics/ingestion, authorized by the
  developer action; model tools remain read-only.

## Planning documents

[spec.md](spec.md) defines the draft product requirements and evidence model.
[roadmap.md](roadmap.md) maps loose modules and proposed acceptance checks.
The active milestone is company-context tooling and evaluation. Interface and
workbook features remain a later backlog.
