# Excel add-in

This Office.js task pane uses the existing research app. Attach up to 200 selected
cells (values and formulas) to the next question, review cited answers, and click
**Insert cited results** to create a new worksheet with claims and evidence.
Selection attachment sends its content to the research backend and, in live mode,
the configured model provider. Selection is a snapshot; reattach after editing.
The combined question and selection must fit the backend's 4,000-character limit.

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

Results always go to a new worksheet. Existing cells are not overwritten. Text
starting with formula markers is escaped. File-based proposals and exports remain
separate; this release does not apply proposals to live cells or continuously sync
the workbook. Repeated insertion creates another worksheet.

Verification: TypeScript/build and browser tests with a mocked Office host cover
connection, selection attachment, and result insertion. Real Excel connection was confirmed on 2026-11-22. The revised live routing
and compact layout are separately tested with deterministic provider/host mocks.

References: [Office.js Excel tutorial](https://learn.microsoft.com/en-us/office/dev/add-ins/tutorials/excel-tutorial),
[Mac sideloading](https://learn.microsoft.com/en-us/office/dev/add-ins/testing/sideload-an-office-add-in-on-mac).

The pane uses Research/Details navigation and a single view at a time. Layout
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

## Task-pane simplification — 2026-11-23

The pane prioritizes asking, inspecting claim-level evidence, and inserting cited
results. Successful connection/provider banners are removed; errors remain visible.
Excel controls scroll with the conversation so they cannot squeeze the answer out
of a short pane. Insertion appears only for an eligible answer. Attached-cell
payloads and research metrics use expandable disclosures. File-workbook tabs are
hidden in Excel until a file workbook exists. Citation chips wrap, expose selected
state, and evidence passages use narrower gutters. Small text has higher contrast.

Design references: [Microsoft Office design principles](https://learn.microsoft.com/en-us/office/dev/add-ins/design/add-in-design)
and [task-pane guidance](https://learn.microsoft.com/en-us/office/dev/add-ins/design/task-pane-add-ins).
Review loop: inspect empty/result/evidence screens, remove competing controls,
check narrow layouts, then repeat browser checks. Screenshots reviewed at 270 and
350 pixels; browser flow checks cover 270, 320 and 350 pixels at 378 pixels tall.
Build, six browser tests, lint, and 626 Python tests passed. Browser tests use
mocked Office/provider responses; this revision was not reverified in native Excel
or against a live model. Existing SQLite ResourceWarnings appeared in Python tests.

Credential loading correction (2026-11-23): local `.env` values override stale
inherited variables. Direct authentication with the file key returned HTTP 200;
the earlier 401 reports came from a different inherited key, not the file key.

After restarting with corrected credential precedence, the live Exa documentation
question completed successfully with five tool calls and a validated cited answer.
The earlier authentication blocker is resolved.
