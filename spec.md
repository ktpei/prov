# Finance research agent specification

Draft for discussion · 2026-11-04

## Purpose and status

Build a finance research assistant that answers questions about companies using
retrieved evidence, explains calculations, and preserves the sources behind its
numbers. The first user-facing workflow is research answers from company data.
The MVP is a standalone browser web app with workbook upload/download. Full
live Excel integration follows the web MVP.

This document describes the intended product and proposed implementation
boundaries. Existing code implements only the foundation described below.
Writing this specification authorizes planning. Later modules require an
implementation task, and live model calls remain deferred.

## Project context

The selected sponsor brief is brief 1 from Provenance × Tech@NYU. It asks for one
model-directed agent loop, 5–7 small tools, a measured 25-task finance evaluation,
and numerical claims with source references. The model chooses its tools and
next action. Deterministic code enforces permissions, budgets, and deadlines.
The original brief and related ideas are summarized in [project.md](project.md).

ProvenanceXL records financial model and presentation versions, changes, and
reasons. This research harness can supply evidence for model inputs and explain
where a proposed input comes from. Integration with the sponsor's add-in,
version store, or proprietary APIs has not been established.

The separate deal-agent brief covers specialist agents, full financial models,
and presentation generation. Those are contextual examples outside the selected
single-agent proof of concept.

## Confirmed product decisions

| Decision | Current position |
| --- | --- |
| First workflow | Research answers from company data |
| Product modules | Chatbot, tooling, evaluation |
| Two-person split | One owner for chatbot, one for tooling and evaluation |
| Runtime | One model-directed loop |
| Existing stack | Python 3.11+, standard-library runtime, CLI, OpenAI Responses adapter |
| Provider | OpenAI first, exact model and live configuration deferred |
| Evidence | Public data under the sponsor's ground rules |
| MVP interface | Browser chatbot with `.xlsx` upload/download |
| Proposed web stack | React + TypeScript + Vite, Tailwind CSS, Python + FastAPI |
| Later Excel integration | Office.js sidebar with live workbook access and approved edits |
| Source packet and companies | Proposed below, awaiting selection |
| Dates and spending | No agreed delivery dates or live-call budget |

## MVP workflow and demo

1. Open the web app in a browser, initially running locally.
2. Select company evidence and a reporting period or information cutoff.
3. Optionally upload a public `.xlsx` workbook. Choose a sheet/range in a table
   preview to provide model context.
4. Ask a research question. Inspect tool activity, the cited answer, source
   passages, units, periods, and calculation inputs.
5. Ask a follow-up using the identified evidence and workbook snapshot.
6. Review proposed cell changes, old/new values or formulas, and sources.
7. Approve before generating an edited copy, then download and open it in Excel.

Deliver browser research and workbook reading first. Approved downloadable edits
form the next MVP increment. Questions may be answered without a workbook.

The three-minute demo shows browser chat, a real cited answer, opening supporting
evidence, and a question about an uploaded range. Once export works, also show
approval, download, and reopening in Excel. Include actual cost, latency, and
reviewed evaluation outcomes. Label scripted/replay material explicitly.

Only single-question CLI execution exists today. The browser UI/API, conversation
state, full-document ingestion, and workbook operations remain unimplemented.

## Planned web architecture

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Frontend | React + TypeScript + Vite | Chat, evidence viewer, activity, workbook preview, approval, download |
| Styling | Tailwind CSS | Interface styling |
| Backend | Python + FastAPI | Sessions, runs, uploads, progress, source access, artifacts |
| Agent/tools | Existing Python harness and OpenAI adapter | Bounded model-directed research and structured evidence |
| Initial storage | Source files and JSON run artifacts | Versioned inputs, citations, traces, output copies |

Start with in-memory conversations and explicit session/run identities. Persistent
chat storage and hosting remain later decisions. Keep credentials on the backend
and expose progress over HTTP. Preserve CLI evaluation alongside the web UI.
Adapt current main-thread POSIX signal deadlines for server execution before
claiming equivalent timeouts and cancellation. Isolate per-run evidence, workbook
context, and budget state for concurrent requests.

Person A owns frontend, API, conversations, and runtime. Person B owns financial
and workbook tools, provenance, and evaluation. Agree upload, progress, answer,
and edit-proposal contracts together.

## What counts as company data

A useful initial evidence packet is a dated collection for one reporting event.
It combines reported financial results with management commentary. The initial
scope should support a few companies and comparable periods before expanding
retrieval breadth. The following is a proposal, not an acquired dataset.

| Material | Questions it supports | Evidence to retain |
| --- | --- | --- |
| Earnings release and financial tables | Revenue, margins, earnings, published outlook | Official URL, date, table or section, period, units |
| Relevant 10-Q or 10-K | Reported statements, definitions, segment detail, footnotes | Filing accession, reporting dates, section or table, source URL |
| Investor or earnings presentation | Guidance, segment narrative, selected KPIs | Original deck, slide/page, date, footnotes |
| Earnings-call transcript or prepared remarks | Guidance qualifications and management commentary | Publisher, event date, speaker, passage, availability limitations |
| Comps workbook supplied as context | Peer selection, existing inputs, valuation calculations | Workbook version, sheet/cell, formula or hardcode, upstream source if available |
| Market-data snapshot, later | Share price, market capitalization, valuation inputs | Provider, timestamp, currency, price definition |

Proposed starting packet size is 2–3 companies, one common calendar reporting
window with each company's fiscal period preserved, and 3–4 available documents
per company. Select a historical cutoff so answers can be reproduced. Keep the
existing five-company excerpt corpus as a small regression suite. Select actual
companies and documents before promising deck or transcript availability.

Official prepared remarks can substitute for unavailable transcripts when the
task can be answered from them. Record the substitution and skip tasks requiring
missing Q&A. Public accessibility, permitted reuse, and extraction quality must
be checked when choosing each source.

SEC company-facts data can help retrieve standardized reported facts. The SEC's
aggregate APIs cover standard-taxonomy, entity-wide facts. Guidance, custom KPIs,
and detailed segment disclosures may require reading the original documents.
[SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)

### How a comps number should be treated

The source role matters as much as the file type. A workbook cell might be a
reported fact, a derived result, or an analyst assumption.

- A reported revenue input should trace to its original filing or release when
  available. A workbook-only citation establishes what the workbook contains.
- A valuation multiple should identify its numerator and denominator, their
  dates and definitions, and the calculation. Trailing and forward measures
  need distinct labels.
- An analyst forecast or selected multiple should be labeled as an assumption
  and attributed to the supplied workbook or analyst instruction.
- Management guidance should preserve the range, forecast period, basis, and
  qualifications from its original release, slide, or transcript.

Example future question — compare the margin assumption in a selected workbook
cell with management's latest guidance available at the task cutoff. The answer
needs both workbook context and the original guidance passage. Any suggested
change remains a proposal until approved.

## Initial research task families

| Task | Expected output | Important failure cases |
| --- | --- | --- |
| Extract a reported metric | Value, unit, period, basis, source passage | Wrong quarter, unit, segment, or accounting basis |
| Find management guidance | Range or statement, forecast period, qualifications | Confusing outlook with actuals or using later information |
| Compare companies or periods | Cited inputs and explicit arithmetic | Unequal periods, mismatched definitions, missing input |
| Explain a discrepancy | Both values and evidence for their different definitions | Inventing a reconciliation without evidence |
| Identify missing evidence | Scoped explanation of what cannot be answered | Guessing a value or claiming universal non-disclosure |

The frozen benchmark already covers extraction, guidance, comparison, and
abstention. Discrepancy analysis and full-document tasks need additional cases.
Qualitative research answers are a proposed extension. The current answer
validator requires factual claims for answerable responses and has no dedicated
structure for qualitative claims.

## Modules and responsibilities

### Chatbot and agent runtime

Accept the question and explicit research context, execute the model loop, and
present the answer with inspectable evidence. Preserve a reproducible CLI entry
point for automated evaluation even if another interface is added.

Continue using the existing loop and provider adapter initially. Conversation
support should make company, cutoff, and carried evidence explicit. Keep gold
answers and evaluator feedback out of model and retrieval context. Do not route
financial task types through scripted workflows.

Bound model calls, tool calls, context, output size, elapsed time, and estimated
spending. Report stops and partial failures explicitly. Preserve the existing
trace and distinguish scripted replay from real inference.

### Tooling and provenance

Tools retrieve or calculate bounded results. Each successful factual result
should retain a stable source identity and a locator sufficient to inspect it.
Search metadata leads to evidence reads. It is insufficient evidence by itself.

| Tool capability | Existing state | Proposed next work |
| --- | --- | --- |
| Search | Frozen corpus and optional Exa adapter | Verify live retrieval and date/source metadata |
| Read source | Numbered local text and Exa content | Ingest full documents and preserve page/table context |
| Filing/XBRL access | Absent | Retrieve facts with filing, concept, unit, and period |
| Market data | Absent | Add dated snapshots when valuation tasks require them |
| Workbook read/write | Absent | MVP upload/read and approved export, then live Excel adapter |
| Python execution | Absent | Define isolation, allowed inputs, limits, and artifact approval first |

The sponsor's 5–7-tool target is a capability goal. Exact tool names and grouping
remain open. Add each tool with a concrete task and evaluator case.

Document text is untrusted input. Tool errors should be visible to the model
without exposing credentials. API keys remain in backend configuration. Proposed
execution tools require an isolation design before implementation.

### Evaluation

The evaluation owner maintains tasks, gold evidence, scoring, human review, and
results. This role includes implementation of the runner and reporting, plus
source QA and failure analysis.

Use the current mechanical pre-grader as a starting point. It checks values,
units, periods, quote presence, and trace consistency. Human review must assess
metric identity, citation entailment, derivations, extra claims, and abstention.
A matching quote alone cannot establish correctness.

For every experiment record task/corpus version, Git revision, model identifier,
prompt/configuration, limits, and run IDs. Report strict task success, claim
correctness, citation validity and support, abstention, tool-error rate, cost,
latency, and stop/failure counts. Define denominators and include failed runs.
Report uncertain charges explicitly. Agree success thresholds before final runs.

Tune on the 10 dev questions. Preserve the 15 heldout questions for an explicitly
authorized final assessment after configuration freeze. The current split shares
companies and source facts, so its results have limited generalization value.
Full-document and workbook tasks need a separately versioned evaluation update
with their own dev/heldout plan before development uses their outcomes.

## Handoffs between the two owners

The chatbot owner owns the research interface, agent loop, provider integration,
and structured answers and traces. The tooling/evaluation owner owns source
retrieval, financial and workbook tools, provenance outputs, benchmark data,
scoring, and review. The chatbot calls tools through agreed schemas and consumes
their results. Evaluation consumes the resulting answer and trace artifacts.
Both agree on tool schemas, task wording, output contracts, and source definitions.

Reuse the current answer fields `answerable`, `answer`, and `claims`, and the
current report fields for run identity, status, metrics, and events. Add required
fields through an agreed versioned contract before either side depends on them.
The current exact-field validator requires coordinated changes for extensions.

Proposed provenance extensions include company identity, metric definition,
accounting basis, original page/table locator, document hash, retrieval date,
and relationships between derived claims and their inputs. Keep original source
locators distinct from local extracted-text line numbers. A source manifest can
hold document-level metadata without duplicating it on every claim.

## Workbook exchange in the web MVP

Uploaded workbooks are snapshots. Retain immutable originals with IDs and hashes.
Bind questions, cell citations, and proposed changes to a snapshot, sheet, and
cell address. Changes in desktop Excel require re-upload. Switching snapshots
invalidates prior edit proposals for the active context.

Read bounded values, formulas, and row/column labels. Distinguish formula text
from cached values. Select the workbook library, supported `.xlsx` features,
and file/range limits during implementation. Initial fixtures should use ordinary
public tables and formulas. Macro-enabled files and embedded features require
separate support work. Explain unsupported inputs clearly.

Preview exact target cells, old/new values or formulas, and sources. Bind approval
to the snapshot and change set before generating a separate edited copy. Preserve
the original and provide a change/provenance record. Retrying should return the
same approved artifact. Partial/failed exports must never appear successful.

Reading/writing alone does not establish recalculation. Select and verify a
calculation strategy before claiming updated formula results. Preserve supported
formulas and formatting, distinguish cached/unverified results, and reopen
representative exports in Excel.

## Later full Excel integration

After the web MVP, add an Office.js task-pane sidebar using the same research
backend and suitable React components. Read live selected ranges/formulas and
apply approved edits directly in Excel. Broader model navigation requires bounded
workbook inspection tools. The backend receives explicitly supplied context.
[Excel add-in overview](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/excel-add-ins-overview)

Select a primary host and supported API requirement sets. Development needs a
manifest, HTTPS setup, and sideloading. Office API mocks support adapter checks.
Real-host checks cover initialization, selection, range access, writes, and
recalculation behavior.
[Office unit testing](https://learn.microsoft.com/en-us/office/dev/add-ins/testing/unit-testing)
[Excel API support](https://learn.microsoft.com/en-us/office/dev/add-ins/reference/requirement-sets/excel-api-requirement-sets)

Recheck affected cells before applying an approved change, reject stale approvals,
prevent duplicate writes, and define partial-write recovery. Prove range reading
and approved insertion before broad edits across model sheets.

## Acceptance and verification

The first research milestone requires a real development run with read evidence,
a structured answer, trace, cost/latency accounting, and human-reviewed citations.
The evaluation pipeline should consume that output and expose its failure modes.
A development result is insufficient evidence for the final sponsor acceptance.

The semester deliverable includes measured evaluation, a one-command runnable
entry point, a three-minute demo, and a one-page report covering measurements,
failures, and cost per task. Numeric targets, exact model, budget, source packet,
workbook support/recalculation, and final evaluation scope remain open.

Verified foundation consists of five curated historical source extracts, 25
tasks, a bounded two-tool loop, provider contract tests, a scripted offline demo,
and a mechanical pre-grader. Live OpenAI/Exa behavior, model quality, full-document
retrieval, and Excel integration are unverified.

## Decisions to resolve

| ID | Question | Proposed starting point |
| --- | --- | --- |
| D1 | Which companies and reporting event? | 2–3 companies, one dated public packet each |
| D2 | Curated document packets, live discovery, or both? | Frozen full-document packets first, live discovery assessed separately |
| D3 | Which research questions matter most? | Reported metrics, guidance, and a supported comparison |
| D4 | Which host for later Excel integration? | Verify desktop Mac or web Excel availability after web MVP |
| D5 | Who owns each workstream? | Chatbot owner and tooling/evaluation owner, names pending |
| D6 | How much time and spending are available? | Agree weekly capacity, delivery date, model, and run budget |
| D7 | What counts as a successful final result? | Agree numeric thresholds and review protocol before final evaluation |
| D8 | Which workbook features and recalculation strategy? | Select fixtures, library, supported edits, and calculation verification |
