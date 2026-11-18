# Excel financial agent research and planning

Research date: November 18, 2026. Status: planning input, not an approved implementation specification.

## Main finding

ProvenanceXL should consider starting with **evidence-backed review and updates to an existing analyst model**. The first complete workflow would explain a selected range, compare it with company disclosures, propose a small set of justified changes, and verify the result in live Excel after approval.

This is a fit with the existing research harness and browser MVP, not a claim of an uncontested market niche. Competitors already offer citations, source links, model auditing, and earnings updates. Differentiation would have to be demonstrated through better handling of financial meaning, explicit uncertainty, review effort, and safe execution on a clearly defined workflow.

There is no single established industry-standard financial agent. There are established spreadsheet practices and several overlapping product categories. Public product documentation establishes advertised behavior, not comparative accuracy or adoption share. This research did not run a hands-on competitor bake-off, purchase subscriptions, or test Office.js in Excel.

## Competitive landscape

### General agents inside Excel

| Product | Documented behavior | Planning implication |
| --- | --- | --- |
| Microsoft Copilot in Excel | Direct workbook editing, chat-only and plan modes, multi-step execution, and finance skills covering model checks, comps, three-statement templates and LBO templates. | A chat sidebar and broad modeling commands are already baseline competition. Separate read-only work from edits; build a complete task experience. |
| Claude for Excel | Multi-tab model understanding, clickable cell citations, assumption updates, formula debugging, template population, financial connectors and reusable skills. | Users will expect workbook navigation and contextual explanations. A cell reference establishes workbook location; original-source evidence still needs its own representation. |
| ChatGPT for Excel | Builds and updates spreadsheets, explains referenced/updated cells, requests permission for changes, and describes formula/format preservation and reversion. Its published limitations include several advanced Excel surfaces and large-workbook context limits. | Match clarity about scope and changed cells. Do not assume that general agent capability implies full Excel feature coverage. |

Sources: [Microsoft getting started](https://support.microsoft.com/en-us/excel/copilot/get-started-with-copilot-in-excel), [Microsoft finance skills](https://support.microsoft.com/en-us/excel/copilot/copilot-in-excel-built-in-skills), [Claude documentation](https://claude.com/docs/office-agents/excel), [ChatGPT product documentation](https://chatgpt.com/apps/spreadsheets/).

These products change quickly. Current documentation supersedes older launch stories describing only formula assistance or beta access. Conversely, a current product page does not establish which features a particular enterprise tenant has enabled.

### Finance specialists and research platforms

| Product | Evidence and scope | What to learn |
| --- | --- | --- |
| Daloopa Scout and Add-In | Builds/updates public-equity models using structured fundamentals. Its GA announcement describes fixed-rule mapping of reported figures into line items and periods. Inspect Cell matches existing model inputs to source-linked data, with an option to retain an analyst's number while adding a connection. | Data identity and mapping are product capabilities, not incidental retrieval details. Separate connecting evidence from overwriting an assumption. |
| Shortcut | Markets an Excel add-in for financial modeling and source tracing. Its separate ShortcutXL desktop offering describes native Goal Seek, data tables, VBA and broader local/connected context. | Distinguish the add-in from desktop automation. Advanced modeling can require a wider execution surface than Office.js alone. |
| Hebbia | Its July 2026 release documents an Excel plug-in for defined workflows and cell citations as Office notes. Its Marketplace listing describes model building, editing and auditing with private project documents and integrated data. | Evidence should travel with the workbook, and repeatable firm workflows matter alongside free-form chat. |
| Rogo | Its June 2026 Microsoft partnership describes finance workflows surfaced through Copilot in Excel for shared customers. | A financial agent can reach Excel through another product's distribution surface. This announcement alone does not establish a standalone add-in's operation or recovery controls. |
| AlphaSense and Carousel | AlphaSense acquired Carousel in October 2025, describing model generation, iteration, source ingestion and model walkthroughs. Current Data & Models documentation separately describes formula-driven refreshable financial data and Canalyst models. | Distinguish data delivery, model libraries and generative editing. Do not treat an acquisition roadmap as proof that all capabilities are available in every package. |
| Finster | Its FAQ describes finance research workflows, branded Excel/PowerPoint exports and private deployment options. | An exportable financial work product is relevant competition, but export alone is not live workbook editing. |

Sources: [Scout GA](https://daloopa.com/blog/product-updates/daloopa-scout-ai-financial-modeling-excel), [Inspect Cell](https://docs.daloopa.com/docs/daloopa-excel-add-in-inspect-cell), [Shortcut](https://shortcut.ai/), [ShortcutXL](https://shortcut.ai/blog/posts/introducing-shortcutxl), [Hebbia release](https://www.hebbia.com/blog/whats-new-july-disclosure-2026/), [Hebbia Marketplace](https://marketplace.microsoft.com/en-us/product/saas/wa200011054?tab=overview), [Rogo partnership](https://rogo.com/blog/announcing-our-partnership-with-microsoft), [Carousel acquisition](https://www.alpha-sense.com/press/alphasense-acquires-carousel/), [AlphaSense financial tools](https://help.alpha-sense.com/hc/en-us/articles/42465162626451-AlphaSense-Financial-Tools-Explained), [Finster FAQ](https://www.finster.ai/resources/news/finster-faqs).

**Material source conflict:** Daloopa's [FAQ](https://docs.daloopa.com/docs/faq) says custom skill uploads and external data/web access are unavailable. Its [dedicated skills guide](https://docs.daloopa.com/docs/using-skills-in-scout) describes custom skills and a document-update workflow, while the GA announcement describes source-document reading. Treat the newer-looking capability descriptions as vendor claims requiring account-level confirmation; do not silently merge these into a verified capability matrix. The FAQ's as-reported versus restated distinction is a useful requirement to test, not a guarantee about every workflow.

### Established data and modeling infrastructure

- **FactSet:** Pitch Creator connects research, templates and charts to Office workflows. Its developer catalog also lists an Excel Model MCP. These are evidence of multiple integration routes, not proof of arbitrary editing of an existing workbook. [Pitch Creator](https://investor.factset.com/news-releases/news-release-details/factset-launches-ai-powered-pitch-creator/), [MCP catalog](https://developer.factset.com/mcp-catalog).
- **LSEG:** Describes licensed data, financial semantics and deterministic analytics delivered through MCP to Claude in Excel and PowerPoint. This supports separating evidence retrieval and computation from narrative reasoning. [LSEG architecture discussion](https://www.lseg.com/en/insights/ai-ready-financial-intelligence-native-in-excel-and-powerpoint-supported-by-lseg).
- **S&P Capital IQ Pro:** Its March 2026 announcement says Drift AI was acquired with planned integration into the Excel plug-in. The source establishes acquisition and intent, not completed rollout. [S&P announcement](https://press.spglobal.com/2026-03-12-S-P-Global-Enhances-Capital-IQ-Pro-with-Expanded-Fixed-Income%2C-Biopharma-and-Private-Markets-Data-Content-and-AI-Capabilities).
- **BamSEC:** One-click filing-table exports demonstrate a narrower alternative to agentic modeling. For extraction-only jobs, a predictable table workflow may be sufficient. [Table export documentation](https://help.bamsec.com/hc/en-us/articles/45646266099347-Download-Tables-to-Excel).

For a future commercial product, data access, redistribution rights, source visibility and user entitlements must be designed together. A connector protocol does not confer a financial-data license. The current project remains public-data scoped.

## What professional quality should mean

The [ICAEW spreadsheet principles](https://www.icaew.com/technical/technology/excel-community/20-principles-for-good-spreadsheet-practice-2024-edition) emphasize understandable input/process/output structure, consistent formulas, simple methods, separated assumptions, review and controls. These are more useful acceptance foundations than a vendor's broad accuracy slogan.

For this product, translate that into observable requirements:

1. **Correct financial meaning:** entity, metric definition, fiscal period, units, currency, consolidated/segment scope, and reported/adjusted status match the intended cell. A matching number alone is insufficient.
2. **Explicit source roles:** distinguish a disclosed fact, management guidance, analyst assumption, derived calculation and unresolved value. A guidance midpoint is a calculation; it is not a directly reported point estimate.
3. **Working formulas:** outputs recalculate when inputs change. Preserve references and conventions; do not replace formulas with plausible hardcodes.
4. **Reviewable changes:** show old/new content, source evidence, transformation, target range and affected outputs. Permit rejection without changing the workbook.
5. **Honest scope:** report which ranges and dependencies were inspected. Avoid calling a selected-range check a whole-workbook audit.
6. **Recoverable execution:** detect stale targets, duplicate requests and partial outcomes. Restore only when doing so will not overwrite subsequent user work.
7. **Portable evidence:** keep useful provenance with the file while retaining a durable run record. Comments and metadata are editable; they are not tamper-proof audit storage.

A single confidence percentage should not replace these checks. Display specific unresolved issues such as an ambiguous period, missing source page or unsupported formula dependency.

## Recommended first workflow

Proposed primary user: a public-equity research analyst updating an existing model after earnings. This follows the current company's-disclosure research scope; user confirmation is still needed before selecting the implementation target.

Example interaction, using a synthetic company until evaluation fixtures are approved:

1. Select the revenue and margin assumptions for the next quarter.
2. Ask the agent to compare them with an attached release and transcript.
3. The agent reads the range, nearby labels/units and relevant dependencies; it retrieves and reads the supporting passages.
4. It returns supported findings and unresolved items. It preserves a deliberate analyst adjustment unless asked to change it.
5. A review table shows each proposed input change, old/new value, unit, period and exact evidence. Any midpoint or conversion is explicit.
6. Approval binds to that proposal and workbook state. The executor rechecks targets, applies supported edits, and asks Excel to calculate.
7. Read-back verifies actual values/formulas and selected dependent outputs. The history records applied, rejected, stale or partially completed outcomes.

This is deliberately a small but complete workflow. Whole-model generation, arbitrary VBA, live market feeds, autonomous scheduled refreshes, simultaneous multi-workbook editing and pitchbook creation would expand both correctness and deployment scope.

Alternative first workflows remain viable:

| Starting point | Benefit | Main limitation |
| --- | --- | --- |
| Explain/check selected cells | Fastest path to live Excel and source inspection | Weaker action value; must avoid exaggerated audit claims |
| Review and refresh selected model inputs | Strong fit with existing harness; clear before/after outcome | Requires financial mapping and robust write/recovery behavior |
| Build a model from scratch | Visually compelling demonstration | Much larger formula, layout, accounting and verification surface; crowded competition |

The second option is the recommendation. It should be narrowed further to one model region and one source packet for the first real-host acceptance test.

## Proposed architecture

Keep the existing Python research service and reusable React components. Introduce an Office.js workbook adapter and a controlled write executor. The model proposes typed operations; it does not receive unrestricted Office.js execution authority.

| Layer | Responsibility |
| --- | --- |
| Excel task pane | Conversation, attached selection, evidence navigation, change review, stop/status and history |
| Workbook adapter | Bounded structure/range reads, formulas, displayed/raw values, formats, worksheet identity and host capabilities |
| Existing research service | Search/read evidence, track actual reads, produce cited answers and justified proposals within budgets |
| Proposal validator | Validate scope, sources, supported operations, target preconditions and financial metadata |
| Excel executor | Re-read preconditions, apply approved operations, calculate, read back, record actual outcomes |
| Durable run/provenance record | Proposal identity, approval, before/after content, source versions, transformations and execution/recovery status |

**Important transport gap:** today's backend reads immutable uploaded snapshots synchronously. A live agent requesting additional workbook ranges needs a client-mediated request/response path with timeouts, cancellation, workbook/run binding and disconnect handling. For the earliest slice, a bounded snapshot attached at send time may be simpler. Do not claim live on-demand reads until that bridge exists.

**Important concurrency gap:** a pre-write read is not an atomic compare-and-swap. Coauthoring can change cells between inspection and application. Start with a declared single-editor pilot, invalidate stale proposals, verify immediately after writes, and test two-user interference before offering broader guarantees. Events help invalidation but are not a durable change ledger.

### Microsoft platform decisions

- Use a task-pane add-in for research and editing. Office.js is cross-platform; COM/VSTO would narrow the deployment to Windows. Declare actual supported hosts/builds and check requirement sets. [Overview](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/excel-add-ins-overview), [requirement sets](https://learn.microsoft.com/en-us/javascript/api/requirement-sets/excel/excel-api-requirement-sets).
- Choose the manifest against the pilot's host matrix. XML remains a production option; unified JSON has newer host requirements. Do not repeat the outdated blanket claim that unified manifests cannot support Excel on Mac. [Manifest options](https://learn.microsoft.com/en-us/office/dev/add-ins/develop/add-in-manifests), [unified support](https://learn.microsoft.com/en-us/office/dev/add-ins/develop/unified-manifest-overview).
- Batch range operations and request only needed properties. Excel web has a 5 MB request/response limit; broad reads require partitioning. Those platform ceilings are not sensible agent-context budgets. [Performance](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/performance), [resource limits](https://learn.microsoft.com/en-us/office/dev/add-ins/concepts/resource-limits-and-performance-optimization).
- Event registrations do not survive add-in reloads. Rebuild subscriptions and re-read relevant state on reconnect. Local/remote change information helps coauthoring handling. [Events](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/excel-add-ins-events), [coauthoring](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/co-authoring-in-excel-add-ins).
- Undo grouping exists through `mergeUndoGroup` on ExcelApi 1.20 hosts, but unsupported operations can throw or clear undo history. Grouping is not a database transaction or guaranteed crash recovery. Keep an operation allowlist and before/after journal. [Undo](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/excel-add-ins-undo-capabilities), [RunOptions](https://learn.microsoft.com/en-us/javascript/api/excel/excel.runoptions).
- Custom functions should compute or retrieve explicit outputs, not mutate unrelated workbook content. They are a later option for refreshable data, not the main agent control channel. [Function restrictions](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/call-excel-apis-from-custom-function).
- For Microsoft identity, evaluate MSAL with Nested App Authentication and a supported fallback. NAA web support currently requires a workbook opened through OneDrive or SharePoint Online; verify the [NAA host requirements](https://learn.microsoft.com/en-us/javascript/api/requirement-sets/common/nested-app-auth-requirement-sets). Backend authorization and tenant isolation remain necessary. A shared demo access code is not enterprise authentication. [NAA](https://learn.microsoft.com/en-us/office/dev/add-ins/develop/enable-nested-app-authentication-in-your-add-in).
- Pilot through sideloading, then an organization's integrated-app deployment. Shared runtime becomes useful if ribbon commands and task pane need shared state; it does not provide unattended execution after workbook closure. [Deployment](https://learn.microsoft.com/en-us/office/dev/add-ins/publish/publish), [shared runtime](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/configure-your-add-in-to-use-a-shared-runtime).
- Persist compact workbook/run references, with recoverable server-side records. Test save-as, copied workbooks, renamed sheets and reopen behavior. Automatic compressed workbook export is not uniform across hosts, so backup cannot assume one universal API. [Persistence](https://learn.microsoft.com/en-us/office/dev/add-ins/develop/persisting-add-in-state-and-settings), [Document API](https://learn.microsoft.com/en-us/javascript/api/office/office.document).

For governance, keep model-provider credentials on the server, scope data sent to the selected task, enforce source access on the backend and record retention rules. Treat workbook/document text as untrusted evidence, including instructions embedded in hidden cells or comments. These are proposed engineering requirements, not claims that the current demo meets an enterprise control framework.

## Fit with the current repository

Inspected `spec.md`, `roadmap.md`, `docs/web-mvp-design.md`, the web workbook/tool modules, API session handling and frontend types. The current browser MVP already has cited conversation, range context, evidence inspection and approved edits to a separate downloadable copy.

Reusable pieces include the research loop, evidence validation, budget tracking, answer/evidence/activity components and proposal-review concepts. Current workbook tools limit reads to 200 cells and proposals to ten edits. These are existing limits, not performance findings about live Excel.

The live add-in still needs host setup, workbook identity and capability detection, a live context contract, change preconditions, execution receipts, actual Excel calculation verification, recovery and durable sessions. The current `openpyxl` export path cannot substitute for a live Office.js executor. Formula syntax checks do not establish correct financial logic.

The harness's newer evidence/calculation work has separate integration gates. Do not assume proposed H3 semantic admission is already in the default web path. Excel delivery and research-quality improvements should retain distinct acceptance criteria.

## Proposed delivery gates

These are sequencing proposals, not estimates or commitments.

| Gate | Deliverable | Acceptance evidence |
| --- | --- | --- |
| 0 | Agree user, first workflow, workbook/source fixture and primary host | Written scope and independently prepared expected outcomes |
| 1 | Read-only task pane with bounded live selection context | Correct formulas/values/labels; citations navigate to correct cells and original evidence |
| 2 | Small approved input updates | Exact reviewed cells change; stale/duplicate proposals are refused; formulas preserved; actual Excel read-back succeeds |
| 3 | Recovery and persistence | Reload/disconnect/partial-write behavior is explicit; conditional restoration does not overwrite newer user edits; history survives reopen |
| 4 | Analyst pilot | Lower total task-plus-review time than baseline without unacceptable errors, with recorded limitations and cost; authentication and tenant isolation qualified before any nonpublic workbook use |
| 5 | Broader modeling and deployment | Additional operations and hosts independently qualified; authentication, tenant boundaries and source entitlements verified |

Before choosing dependencies or building the UI, settle the first host and whether the deliverable is our own add-in or integration with the sponsor's existing one.

## Evaluation design

Existing financial question-answering evaluations do not establish workbook editing reliability. Keep three separate dimensions: factual/source correctness, workbook/formula correctness and execution/recovery correctness.

Research supports this separation. [MBABench v5](https://arxiv.org/abs/2605.22664v5), initially indexed under WorkstreamBench, evaluates accuracy, formulas and formatting. [BlueFin](https://arxiv.org/abs/2605.30907) highlights dynamic correctness. [SpreadsheetBench 2 v2](https://arxiv.org/abs/2606.29955v2) identifies insufficient inspection and wrong target-cell selection as prominent failures. These are paper-reported findings under their own setups, not a current ranking of commercial add-ins. Only abstract/metadata pages were consulted; task workbooks and source reports were not opened.

A proposed acceptance suite should include:

- Normal supported edits with independently checked expected values/formulas.
- Wrong units, quarterly versus year-to-date ambiguity, missing period labels, restatements, adjusted metrics, and an analyst override that should remain intact.
- Formulas that must continue to work after an input perturbation, not merely match a cached result.
- A source citation that exists but does not support the proposed metric.
- A user change after proposal, repeated approval, sheet rename, workbook switch, protected range and spilled-array target.
- Network failure, add-in reload and an interrupted multi-cell operation.
- Active cell-edit mode: batches can fail or defer through `delayForCellEdit`; recheck preconditions after deferral rather than applying an old proposal blindly.
- A coauthor change during execution and attempted recovery after later user edits.
- Prompt-like instructions inside workbook/source content that must not expand action authority.

Track task success, correctness of target cells, unsupported-change rate, evidence support, formula preservation, recovery success, abstentions, latency, model cost and human review time. Report denominators and failure examples. Zero observed failures on a small fixture set does not justify a general reliability claim.

Vendor benchmark claims should remain separate. Shortcut's homepage labels its July 2026 comparison an internal evaluation over 20 tasks; its figures should not be combined with research-paper scores or our harness results.

### Evaluation reservations preserved

Before research, consulted the FinanceBench reservation and exposure audit, plus the existing corpus source metadata. The six reserved issuers remain Lockheed Martin, American Express, Amazon, Microsoft, AMD and Block/Square. Amazon and Microsoft retain their recorded prior issuer exposure; these are not six unseen issuers. Other reservations and unresolved aliases remain unchanged. No held-out task bodies or issuer financial-source content were opened for this work. Microsoft product documentation is platform research, not issuer-financial development material.

## Brainstorming decisions

1. Who is the first user: public-equity analyst, investment-banking analyst or FP&A professional? Their source systems and model conventions differ materially.
2. Is the first value proposition explaining/checking a model, updating an existing model, or generating a model? Recommendation: reviewed updates to a selected region.
3. Is this a new independent add-in or a module within the sponsor's add-in?
4. Which Excel host and build can we actually test first? Recommendation: one primary host, with cross-platform design and additional host acceptance later.
5. What source inputs are allowed initially: curated public packet, uploaded documents, or broader retrieval? Recommendation: a bounded public packet for the first verified workflow.
6. What edits are in scope? Recommendation: selected input cells first, with explicit exceptions for formulas and structural changes.
7. What makes the pilot successful: fewer unsupported inputs, faster earnings refresh, less reviewer time, or a compelling end-to-end demonstration? Pick one primary measure and correctness gates.

Confidence is high in the landscape categories, baseline workflow expectations and major platform constraints. Confidence in the proposed first workflow is provisional because it depends on the user's target analyst and sponsor integration. Relative competitor accuracy, actual tenant availability, commercial terms, user willingness to switch and real-host behavior still require direct testing or customer input. Further generic market searching has lower value than resolving those choices and running a small controlled pilot.
