# Excel add-in

This Office.js task pane captures the open desktop Excel workbook before each
question so the agent can read cells, cite them and propose ordinary input edits.
Attach up to 200 selected cells to identify a focus range. Review proposals in
**Changes** before applying them to Excel. **Insert cited results** creates a new
worksheet containing answer claims and evidence.

Workbook snapshots are sent to the research backend; requested ranges are shared
with the configured model provider. Each new question captures current contents;
there is no continuous synchronization.

## Local setup

1. Install dependencies: `npm --prefix web install`.
2. Start the backend: `uv run python -m provenance.web` (port 8765).
   Keep `OPENROUTER_API_KEY` and `EXA_API_KEY` in `.env`.
   Set the model, accounting rates, and spending limits in `research.config.json`. Research uses live Exa search and fetched text;
   missing configuration disables research, with no demo fallback.
3. In another terminal run `npm --prefix web run excel`. The Microsoft development
   certificate helper may prompt you to trust its localhost certificate.
4. Sideload `office/manifest.xml` into Excel. On Mac, copy it into
   `~/Library/Containers/com.microsoft.Excel/Data/Documents/wef/` (create the folder
   if needed), restart Excel, then select the add-in from the add-ins menu.
5. Open a workbook, select cells, and open Provenance Research.

The manifest points to `https://localhost:3000/?excel=1`. Vite proxies the API to
port 8765, keeping requests on the same origin. Both servers must remain running.
For deployment, host the app and API behind HTTPS and update SourceLocation.
This is a sideloadable development add-in, not a Marketplace installation.

Answer insertion always creates a new worksheet. Approved input proposals can
update existing ordinary cells through the separate Changes flow described below.
Text starting with formula markers is escaped. File-based exports remain separate;
there is no continuous sync. Repeated answer insertion creates another worksheet.

Verification: TypeScript/build and browser tests with a mocked Office host cover
connection, selection attachment, and result insertion. Real Excel connection was confirmed on 2026-11-22. The revised live routing
and compact layout are separately tested with deterministic provider/host mocks.

References: [Office.js Excel tutorial](https://learn.microsoft.com/en-us/office/dev/add-ins/tutorials/excel-tutorial),
[Mac sideloading](https://learn.microsoft.com/en-us/office/dev/add-ins/testing/sideload-an-office-add-in-on-mac).

The pane uses one Research/Evidence/Activity navigation row and a single view at a time. Layout
checks cover 270, 320, and 350 pixel widths at 378 pixels tall. The upper-right
40 pixels are reserved for Office controls. Replay controls, fixed evidence
packets, sample questions, and demo workbook loading are removed from the app.
Offline benchmark fixtures remain separate from the product.

Verification on 2026-11-22: live Exa search returned five results and an explicit
source read returned numbered evidence. The full live answer smoke failed before
any tool call because OpenRouter returned an authentication error; replace the
configured OpenRouter credential and restart the backend to verify full answers.
The app never falls back to recorded answers.

2026-11-23: `.env` contains credentials only. `research.config.json` holds model,
accounting rates, Exa request allowance, per-question cap, and total ledger cap.
The launcher loads both files; restart the backend after edits. Current prices
are supplied estimates, not automatically fetched provider metadata.

Credential loading correction (2026-11-23): local `.env` values override stale
inherited variables. Direct authentication with the file key returned HTTP 200;
the earlier 401 reports came from a different inherited key, not the file key.

After restarting with corrected credential precedence, the live Exa documentation
question completed successfully with five tool calls and a validated cited answer.
The earlier authentication blocker is resolved.

## Web-derived pane layout (2026-11-23)

The rejected simplification was reverted in `09f2063`. The replacement restores
the original web interface's dark provenance mark, answer cards, ledger-green
citations, and paper-style evidence viewer. A single navigation row replaces the
nested Research/Details tabs. Excel attachment and insertion controls sit in the
question composer; insertion appears when an eligible answer exists. Attached
cell payloads are expandable in question history. Workbook/Changes navigation is
available after the first workbook snapshot is captured. Live Excel insertion still targets the
latest completed answer when eligible and creates a new worksheet.

Visual review covers the welcome, answer and evidence views at narrow pane sizes,
plus a 350 × 760 full-height pane. Seven browser tests use deterministic Office
and provider mocks. Native Excel has not been visually rechecked for this revision.

### Selection attachment

Select cells in Excel, then choose **Attach selected cells**. The composer shows
the captured sheet/range and cell count, with an expandable value preview.
**Update from selection** replaces the snapshot with the currently selected range;
the remove control clears it. Editing cells or moving the Excel selection does not
change an existing attachment. The range address is sent with the next question, and current cell values/formulas
are read from a fresh workbook snapshot. A rejected update preserves the previous attachment.

Verified in native Excel on 2026-11-23: the card displays `DCF!E6` and one attached
cell. Eight browser checks cover the UI, snapshot replacement, oversized-selection
failure, removal before submission, and narrow-pane layout. Build and lint passed.

### Temporary research execution settings (2026-11-23)

Excel/web research has no tool-call count, model-step count, or overall run-time
cutoff (`TURN_LIMITS` uses `None` for those three fields). Individual requests still
have a 30-second timeout. The configured per-question and total spending caps
remain active; removing execution caps does not remove spending controls. CLI and
benchmark defaults remain bounded. Regression checks cover a completed 13-step,
12-tool-call graph run and a spawned worker with the execution caps disabled.
Restart the backend after changing these settings; existing sessions are in memory.

The evidence and activity views include a **Back to research** button. Activity
uses separate icon, wrapping content, and time/cost columns to fit narrow task
panes. The header omits the provider label and the welcome view omits introductory
body copy. Live research remains available through the question composer.


## Workbook tools and approved input changes (2026-11-23)

Desktop Excel on Mac/Windows captures the open workbook before each question
and uploads it to the research server. This enables `read_workbook_range`,
cell citations and `propose_cell_edits`; an attached selection focuses the
current snapshot on that range. The composer states that questions share the
workbook. Failed capture stops submission and preserves the question.
Compressed snapshots are unavailable in Excel on the web/iPad; these hosts
show an explicit error rather than silently asking without workbook tools.
See [Microsoft's host support matrix](https://learn.microsoft.com/en-us/javascript/api/office/office.document).

Review proposals in **Changes**, then choose **Approve … in Excel**. This requires
ExcelApi 1.13. Before writing, the add-in checks worksheet identity, typed old
values and that every target remains a visible, unprotected ordinary input,
outside merged areas, tables and spill ranges. Formula cells cannot be replaced.
Excel recalculates; input readback must match before the session records an
applied receipt. Ask a new question to capture results for subsequent citations.

Workbook captures retain the existing .xlsx, 5 MB and 30-sheet limits. Macros
are rejected. Existing export blockers (including charts/pivots and unsupported
metadata) conservatively prevent edit proposals; this change does not widen
workbook eligibility. Saved formula caches may be stale before application.
Office write batches are not transactional: uncertain failures ask you to inspect
the affected cells and refresh. No automatic retries or rollback are attempted.
Successful writes with a failed server receipt are reported distinctly.

Verification: four backend route tests and 17 Excel browser checks with mocked Office
and providers passed. Native Excel capture and edit application, and a live
model DCF driver-update task, have not yet been verified.
