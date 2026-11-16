# Your handoff: research UI and agent integration

> **Note for agents:** This document is for human reading. Address the teammate
> directly as “you,” use plain language, and explain the purpose of the work
> before implementation details. This is a handoff, not authorization to start
> implementation, spend money, or change evaluation boundaries.

## Your high-level overview

You have a research engine working behind the scenes. It can search company
documents, read supporting passages, and return answers with citations. Your
main job is to make those capabilities easy for someone to use.

**Your UI north star is something similar to the Excel plugin Provenance already
has.** Use their existing plugin as the reference for the overall look, layout,
and interaction style, so your research experience feels familiar alongside
their product. Review the plugin with the team before making detailed design
choices. This is a design direction; connecting to the live Excel workbook
remains a later implementation step.

You will mostly build the user experience, plus the connection between the
interface and the research engine:

- **Build the question-and-answer screen.** Let someone choose the available
  company documents, ask a question, and read a clearly formatted answer.
- **Show what is happening.** Show when the assistant is searching, reading, or
  finishing its answer. Explain when it cannot answer or something goes wrong.
- **Make sources easy to check.** Let someone click a citation and open the
  supporting passage to verify where a number came from.
- **Make the experience reliable.** Keep results available after a page refresh,
  prevent duplicate paid requests, keep different users’ research separate, and
  make the stop button actually stop the work.
- **Add follow-up questions.** Decide what the assistant should remember and when
  it should start fresh, especially when someone switches companies.

Your first milestone is simple: **someone can ask one question, watch the
research progress, and inspect the sources behind the answer.** Start with a
clearly labeled recorded example, then connect live research.

You will coordinate with the tooling/evaluation owner, who continues improving
how reliably the engine finds and interprets financial evidence. A polished
interface does not establish that every answer is financially correct; that
still needs testing and review.

You do not need spreadsheet uploads, cell editing, or workbook exports for this
first delivery. Excel integration comes later.

## Your starting point

Snapshot: November 16, 2026. The inspected implementation was on
`codex/finance-benchmark-loop` at `49a5ddb`.

You own the research interface and the API connecting it to the existing Python
agent. The proposed stack is React, TypeScript, Vite, Tailwind, and FastAPI. The
browser/API layer is not implemented yet. Existing planning documents defer UI;
this handoff proposes your next increment rather than changing the active
milestone automatically.

Keep the existing single-agent LangGraph runtime. Coordinate financial tools,
evidence schemas, and evaluation changes with the tooling/evaluation owner.

You can build on:

- LangChain/OpenRouter integration and a model-directed LangGraph research loop.
- Default `search_sources` and `read_source` tools, bounded evidence, source
  identities, and citation checks.
- Native HTML/PDF ingestion and a four-document Cloudflare research packet.
- Limits on model calls, tool calls, time, and estimated spending.
- Final synthesis and one bounded citation-repair attempt.
- SQLite checkpoints with explicit pause/resume and cached completed results.
- Structured answers, event traces, run metrics, and independent evaluation.

The offline LangGraph demo was verified during handoff preparation: completed,
three replayed model calls, two tool calls, zero tool errors, and $0 cost. Treat
this as a plumbing check, not evidence of model accuracy.

Table tools and typed XBRL readers remain experimental and separate from the
default agent loop. Do not present them as working chatbot capabilities yet.

## Your first deliverable

Build one complete research flow before expanding features:

1. Let someone choose a supported source packet and enter a question.
2. Start a run with visible configuration and limits.
3. Show actual search/read activity and recoverable tool errors.
4. Render the answer with units, periods, and clickable citations.
5. Open the exact supporting passage alongside the answer.
6. Preserve the result across a browser refresh.
7. Explain failures, limit stops, cancellation, and abstention clearly.

Start with offline replay so you need neither credentials nor paid calls for UI
development. Label replay explicitly. Add live inference after you verify the
API lifecycle. Ship single-question runs first if the follow-up contract is not
ready.

## Harness details you need to preserve

**Separate sessions from runs.** Give each conversation a session identity and
each execution a run identity. A LangGraph `thread_id` currently identifies
checkpointed execution of a fixed question; it is not a multi-turn chat session.

**Define follow-up context.** Decide which messages, evidence, source packet,
and information cutoff carry forward. Do not silently carry incompatible
evidence into a question after the user changes company or packet.

**Isolate mutable state.** Source objects contain documents, read-evidence state,
and budget references. Isolate these per execution. Test simultaneous sessions
for evidence, accounting, and checkpoint leakage.

**Adapt deadlines for the server.** Current enforcement uses main-thread POSIX
signals. Calling the synchronous runtime from a FastAPI worker thread is not
sufficient. Choose and test an execution approach that preserves deadlines,
cancellation, and accounting.

**Implement cancellation on the backend.** Closing a progress connection or
hiding a spinner does not mean a run stopped. A request already sent to a
provider may still incur charges. Preserve uncertain-cost reporting and
distinguish cancellation requested from confirmed termination.

**Reconnect without rerunning inference.** Add stable progress-event identifiers
and reconnect behavior in your API adapter. Refreshing or submitting twice should
reconnect to or return an existing run instead of duplicating a paid request.
These protections still need implementation.

**Keep retry separate from resume.** Only explicit tool-boundary pauses are
safely resumable. Failed/stopped runs need new execution identities. Unexpected
interruption during a provider attempt requires billing review; do not bypass
the durable attempt marker. Return cached results for completed executions.

**Preserve checkpoint compatibility.** Existing checks include question,
model/mode, limits, corpus hashes, pricing, runtime policy, retrieval version,
and read format. New prompt/schema/projection compatibility guarantees remain
proposed work.

**Show observable progress.** Use actual events for search started, source read,
tool error, final synthesis, and completion. There is no existing browser
token-streaming contract. Do not invent reasoning steps or percentages.

**Distinguish traces from model context.** Canonical evidence is retained, while
model context projects bounded tool results and may omit older reads.
Model-visible evidence receipts remain proposed work. Do not claim that every
stored passage was visible during final synthesis.

**Keep budget state on the server.** Preserve per-run limits, conservative
reservations, uncertain charges, and final-answer headroom. A per-run cap does
not enforce an aggregate account/day cap. Reconcile the latest spending ledger
before paid testing; historical authorization paragraphs contain older balances.

## Your answer and evidence contract

Reuse the current validated answer shape:

- Answer: `answerable`, `answer`, `claims`.
- Claim: `key`, `value`, `unit`, `period`, `citations`.
- Citation: `source_id`, `locator`, `quote`.

The validator requires exact fields. Put UI metadata in an API envelope and
coordinate versioned changes before extending the core schema.

Preserve the run report’s `run_id`, `status`, `stop_reason`, `answer`, `metrics`,
and runtime identity. Handle `completed`, `paused`, `stopped`, and `failed`.
Any queued/cancelling UI states are additional API states you must define.

Treat abstention as a valid result: `answerable: false`, explanatory answer text,
and no claims. Never present a stopped or failed run as a completed answer.

For source inspection:

- Resolve citations against the run’s identified evidence, not a newly fetched page.
- Preserve quoted text and local line locators.
- Show original page/section/table information when available. Local `L4-L6`
  does not mean an original document page.
- Preserve document identity, units, fiscal periods, scale, and available caveats.
- Explain citation checking accurately: structure and quote presence do not
  establish financial correctness.

Keep credentials backend-only. Expose bounded, session-authorized source access
instead of arbitrary filesystem paths. Render source text as untrusted content.

## Your ownership boundary

You own the browser experience, source viewer, run endpoints, progress delivery,
session isolation, cancellation, reconnect behavior, and follow-up integration.

Your tooling/evaluation partner owns extraction, retrieval, financial evidence,
table/XBRL integration, calculation contracts, benchmark protocols, and semantic
review.

Agree together on versioned API/output contracts, new tool schemas, evidence
carryover, checkpoint compatibility, and acceptance fixtures.

Defer workbook upload/export, Office.js, spreadsheet writes, market-data
expansion, arbitrary Python execution, and autonomous analyst teams. The
eventual product remains an Excel add-in.

## How you know the first increment is ready

- You can run the offline fixture through the browser and inspect its citations.
- Actual runtime events drive progress and terminal states.
- Refresh/reconnect does not duplicate execution.
- Concurrent sessions cannot access each other’s evidence or run state.
- Timeout, cancellation, tool failure, abstention, and uncertain cost render correctly.
- Pause/resume preserves accounting and rejects incompatible resumes.
- Evaluation can still call Python directly without the UI.
- `yarn lint`, `yarn test`, and focused API lifecycle checks pass.

Then perform an authorized live development run, inspect its citations, and
record the configuration, results, limitations, and estimated cost.

## Where you should start reading

Read [README.md](README.md), [roadmap.md](roadmap.md), and [spec.md](spec.md) for
intended boundaries. Reconcile older status paragraphs with current code and
dated reports: some planning text still describes capabilities as absent or
pending after later experimental work landed.

Your main implementation entry points are:

- `provenance/graph.py`: execution, checkpoints, finalization, run reports.
- `provenance/agent.py`: limits and trace events.
- `provenance/langchain_model.py`: OpenRouter adapter.
- `provenance/sources.py`: default tools and citation checks.
- `provenance/model.py`: answer validation.
- `provenance/context.py`: model-context projection.
- `provenance/controls.py`: deadlines and spending.
- `provenance/__main__.py`: configuration and invocation.
- `tests/test_graph.py`, `tests/test_agent.py`: runtime regression behavior.
- [Harness research](eval/finance-harness-research-2026-11-16.md): proposed
  improvements, not implemented guarantees.

Run these from the repository root:

```sh
uv sync --locked
uv run python -m provenance demo --engine langgraph
```

At inspection, five XBRL assessment files were untracked:

- `eval/assessments/xbrl-evidence-delivery-v1/source-requirements.json`
- `eval/scripts/run_xbrl_delivery.py`
- `provenance/xbrl_assessment.py`
- `tests/test_xbrl_assessment.py`
- `tests/test_xbrl_delivery_run.py`

Treat them as in-progress work. Coordinate ownership before editing or committing
them; recheck the checkout because this snapshot may change.

Keep evaluation reservations intact. Do not use Lockheed Martin, American
Express, Amazon, Microsoft, AMD, or Block for new development tuning. Consult
the reservation and exposure audit before selecting sources. Amazon and
Microsoft already have documented issuer exposure. Preserve original holdouts
and keep gold answers out of runtime/UI fixtures.
