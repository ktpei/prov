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
   Configure `OPENROUTER_API_KEY`, `EXA_API_KEY`, and a positive
   `EXA_MAX_REQUEST_USD` in `.env`. Research uses live Exa search and fetched text;
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
