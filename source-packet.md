# Candidate research packet — Cloudflare 2024

Researched 2026-11-07. Candidate for the company-context tooling milestone, not
an acquired corpus, frozen benchmark, or model-quality result. Cloudflare is
outside the existing five-company benchmark, avoiding reuse of its heldout facts
for new development tasks. Start with one company before adding peer comparison.

## Public source inventory

| Source | Role | Verification |
| --- | --- | --- |
| [Q3 2024 earnings release](https://www.cloudflare.net/news/news-details/2024/Cloudflare-Announces-Third-Quarter-2024-Financial-Results/default.aspx) | HTML financial tables, actuals, guidance, non-GAAP reconciliation | Official release located; indexed text inspected |
| [Q3 2024 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1477333/000147733324000085/cloud-20240930.htm) | Full filing, definitions, statements, notes, risks | SEC indexed text inspected; accession 0001477333-24-000085, filed 2024-11-07, period 2024-09-30 |
| [Q3 2024 call transcript](https://www.cloudflare.net/files/doc_financials/2024/q3/CORRECTED-TRANSCRIPT_-Cloudflare-Inc-NET-US-Q3-2024-Earnings-Call-7-November-2024-5_00-PM-ET.pdf) | Management explanations, qualifications, analyst Q&A | PDF text opened; 18 pages, event 2024-11-07; FactSet copyright, hosted by company |
| [Investor Day investor-session slides](https://www.cloudflare.net/files/doc_downloads/Presentations/2024/05/Cloudflare-Investor-Day-2024.pdf) | Strategy, investor narrative, chart/table extraction | Linked from official 2024-05-30 event; reader hit 14.7 MB size limit, contents not inspected |
| [Investor Day event page](https://www.cloudflare.net/events-and-presentations/events-calendar/event-details/2024/Cloudflare-Investor-Day-2024/default.aspx) | Deck provenance and event date | Opened; links investor-session slides and separate keynote slides |

Use a proposed cutoff of 2024-11-08 for research questions. The May deck predates
the Q3 results; preserve its date and never present its metrics as Q3 actuals.
Transcript correction/publication timing needs checking before claiming strict
historical availability at that cutoff. Public hosting does not establish a
redistribution license: check reuse before committing full source copies,
particularly the third-party transcript. Source links alone do not prove complete
or accurate extraction. No original document has been added to this repository.

## Proposed development questions

These are task ideas, not scored gold answers. Locate exact passages and review
expected answers before freezing tasks.

- Extract reported Q3 revenue and year-over-year growth with period and units.
- Find Q4 revenue guidance and distinguish outlook from reported results.
- Compare GAAP and non-GAAP operating performance; trace the reconciliation.
- Explain management's account of the change in dollar-based net retention.
- Compare the earlier investor narrative with Q3 management commentary, preserving
  dates and distinguishing management statements from analyst inference.
- Find a definition or footnote in the full filing that qualifies a headline KPI.
- Ask for information deliberately absent from the packet; assess scoped abstention.

## Search/read contract to polish

Keep two agent tools. Ingestion, parsing, indexing, and manifests are supporting
infrastructure, not extra agent tools.

- `search`: query within explicit company/packet/cutoff context. Return source IDs,
  matching passage locators, titles, source types, dates, and retrieval snippets.
  Search results guide reading; they are not final claim evidence.
- `read_source`: inspect a bounded passage/page/section from an identified source,
  preserving headings, units, table headers, footnotes, and original locators.
  Expose navigation and completeness; report truncation or missing extraction.
- Preserve immutable source identity/hash and distinguish original page/section
  locators from extracted-text line numbers. Summaries cannot replace raw evidence.
- Start with full-text document search and inspect failures before deciding whether
  embeddings or a vector store are necessary.
- Google Docs can later be ingested through an explicitly accessible export or
  supplied file; private Drive access and universal format support are not implied.

Current baseline ranks 20-line passages with lexical overlap and returns a best
match locator and snippet. Parser-supplied page-text packets preserve page maps.
Existing gaps: raw PDF/layout parsing is absent; Exa reading
caps content at 16,000 characters and caches only that text. Stable local lines
exist, but original PDF pages and table structure are not preserved. These tools
must not be presented as full-document navigation yet.

## Stack options checked

Current implementation: Python standard library custom loop, raw HTTP direct
OpenAI Responses adapter, optional Exa adapter, unittest and Ruff. No agent SDK.

LangChain + LangGraph are selected for the target runtime. Begin with one
LangChain research agent using search/read; use LangGraph state/checkpoints and
later explicit approval/resumption workflows as needed. Migration must preserve
limits, accounting, trace contracts, citation validation, and replay tests.
Evidence storage and evaluation stay independent of the agent framework.
An initial adapter/graph migration is implemented. Dependencies are installed
and locked; all 44 offline tests pass, including graph execution. Page-text
ingestion and passage search are tested. Live provider acceptance and actual
company document ingestion remain pending.

Extraction candidates: native text extraction, Docling for structured conversion,
and Unlimited-OCR for difficult/scanned documents. Compare financial numbers,
headers, footnotes, reading order, and page attribution before adoption. OCR
long-document efficiency does not itself solve research context bloat. Keep
stored evidence, persisted workflow state, and per-turn model context distinct.

References inspected 2026-11-07:

- [LangChain agents](https://docs.langchain.com/oss/python/langchain/agents)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [Unlimited-OCR](https://github.com/baidu/Unlimited-OCR)
- [Docling chunking](https://docling-project.github.io/docling/concepts/chunking/)
- [OpenRouter tool-calling loop](https://openrouter.ai/blog/tutorials/tool-calling/)
- [Pydantic AI OpenRouter provider](https://pydantic.dev/docs/ai/models/openrouter/)
- [Pydantic AI agents](https://pydantic.dev/docs/ai/core-concepts/agent/)
- [Pydantic AI output validation](https://pydantic.dev/docs/ai/core-concepts/output/)
- [OpenAI Agents SDK model/provider options](https://openai.github.io/openai-agents-python/models/)
- [Exa contents API](https://exa.ai/docs/reference/get-contents)

OpenRouter supplies model access, not Exa search credentials or document ingestion.
Actual compatibility, tool calling, output handling, and cost accounting must be
verified against the chosen model/provider route. No live SDK acceptance was run.
