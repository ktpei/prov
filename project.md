# Project scope

Informal, unpaid, part-time proof of concept for ProvenanceXL. The selected brief
is a single model-directed finance agent with a small tool set and an honest
evaluation. Current authorization covers roadmap steps 1 and 2 only.

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

Full filing/XBRL extraction, financial-calculation tools, market data, workbook
reading/writing and approval UI, full benchmark execution, model/prompt tuning,
deployment, a production UI, and a production financial research service.

## Decisions

- Python 3.11+ standard-library CLI; no framework required for two tools.
- OpenAI Responses API for future inference; no paid model chosen implicitly.
- Frozen-corpus retrieval works without Exa. Optional Exa search/contents is
  implemented but not live-verified.
- Runtime has no model-controlled file writes. Human-supplied `--log-dir`
  explicitly enables deterministic diagnostic logging.
- One model loop at runtime. Development research/review delegation is separate
  from the product architecture.
- No remote repository was configured in this initially empty workspace.
