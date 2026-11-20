# Browser workbook review milestone

Date: November 20, 2026. Status: implemented and verified offline.

## Outcome and stopping point

An analyst uploads an existing `.xlsx`, navigates to a relevant range, inspects
saved values and formulas, asks a cited research question, reviews proposed input
changes, and downloads a checked separate copy with a provenance record. The
uploaded original is immutable. The browser is a review workspace, not an Excel
calculation engine or an interface to an open desktop workbook.

This milestone stops when that bounded workflow passes automated browser and
backend acceptance checks. It does not claim financial correctness from citation
presence, validate all workbook logic, or claim that exported formula results
have recalculated. Analysts open the copy in Excel to recalculate and review
outputs. Live Excel integration remains M7.

## Existing foundation and new work

The browser MVP already provides chat, evidence inspection, workbook upload,
selection context, proposal approval and cumulative exports. This milestone adds:

- Bounded navigation beyond the first 60 rows and 26 columns, with a direct range
  field, paging, correct absolute addresses and offscreen citation navigation.
- A selected-cell inspector showing formula, saved value, cached-result status
  and edit eligibility. Missing formula caches must not look like zero or empty
  inputs. Controls work with a keyboard as well as pointer selection.
- Explicit supported-edit boundaries enforced both when proposing and exporting.
- Export integrity checks, visible calculation status and accessible export history.
- Clear current-snapshot versus old-citation/export handling.

## Supported workbook contract

Accept `.xlsx` only, at most 5 MB compressed and 30 worksheets; validate expanded
archive limits before loading. Workbook content is data, never instructions to
expand tool permissions. The current public evidence sets remain unchanged.

Read workbook regions in bounded windows, up to 60 rows by 26 columns per preview.
Allow a typed A1 range to select within a window; attach up to 400 cells as research
context. Agent reads remain capped at 200 cells and proposals at ten per turn.
Show raw saved values separately from formatted display and formula text.

Edits in this milestone change ordinary input values/text only. Existing formula
cells, merged ranges, protected sheets, hidden sheets and table cells are
read-only. New formulas and structural edits are not supported. Existing formulas
remain intact. This deliberately tightens the earlier demo's formula-write
behavior until calculation and dependency verification have a separate milestone.
Workbook features whose fidelity cannot be checked (including charts, images,
pivots, chart sheets and external links) make export unavailable, with reasons;
reading remains available where parsing supports it.

## Interaction

1. Upload or choose the labeled demo. See workbook identity, limitations and
   available sheets. Switching uploads invalidates pending proposals.
2. Select a sheet and enter a range, or use row/column paging. Click/Shift-click
   cells or use the keyboard to select. Inspect the selected cell without relying
   on hover or color alone.
3. Attach the range and ask a question. Distinguish workbook values, assumptions
   and reported evidence. Formula caches are saved historical values, not fresh
   calculations.
4. Review each proposal's old/new value, rationale and evidence. Approval creates
   a separate cumulative copy; it does not change browser snapshot values.
5. See verification status and download the copy. History identifies the source
   snapshot. Re-upload a downloaded copy to begin a new review version.

An old workbook citation must never silently highlight the same address in a
new upload. Grid requests must not let a slow response replace a newer sheet or
range. Unsupported targets fail before a proposal or file can be accepted.

## Export guarantees and limitations

Validate targets again at export, reject conflicting/duplicate targets and stale
preconditions, preserve existing cell comments when adding provenance, preserve
non-target values/formulas, and reload the saved file to verify intended changes.
Failed verification produces no downloadable result. Audit text must be stored as
text, not executable spreadsheet formulas. Each exported copy includes an audit
sheet and changed-cell source comments, snapshot identity, approval time and
live/replay origin.

Report verification as content/formula preservation and applied-input checks,
not financial-model validation. Request automatic/full recalculation on opening
in Excel; browser results are not recomputed. Repeat approval is idempotent and
separate approvals remain cumulative for the same original snapshot.

Sessions/history remain in memory for this local/pilot milestone. Restarting the
server loses the session; this is not enterprise storage, shared-workspace access
control or a production deployment milestone. Existing cost limits remain in
force; offline tests/replay do not authorize a new paid model batch.

## Acceptance gates

- Navigate and attach a synthetic range beyond row 60/column Z; absolute labels,
  selection and read context agree. Invalid/out-of-bounds windows are rejected.
- Inspect both cached and uncached formula cells; neither is presented as a
  freshly calculated result. Formula targets and unsupported workbook features
  cannot bypass export controls through direct API calls.
- Review and approve the existing replay workflow, download a valid copy, verify
  changed inputs, preserved formulas/comments and provenance. No model call is
  implied by replay success.
- Exercise stale upload/citation, invalid range, blocked edit, duplicate approval,
  cumulative exports and non-target preservation with meaningful regression tests.
- Run `yarn lint`, `yarn test`, frontend production build and Playwright browser
  tests; inspect the resulting browser view visually.

## Later milestones

1. Formula editing and recalculation, with a defined calculation engine and
   compatibility suite; dynamic correctness and dependency checks.
2. Versioned server persistence and authenticated collaboration if needed for a
   hosted analyst pilot.
3. Office.js live adapter: workbook identity, capabilities, coauthoring/stale
   checks, approved execution, read-back, undo and partial-write recovery.
4. Broader model generation, structural changes and licensed data integrations
   only after their own correctness and entitlement requirements are agreed.

The product direction follows the [industry research](excel-agent-research-2026-11-18.md).
The underlying evidence harness and evaluation reservations are unchanged.

## Verification result

November 20, 2026: lint, all 596 Python tests in the combined working tree,
frontend production build, and all six Playwright tests passed. Python totals
include pre-existing untracked XBRL tests, which are not part of this change.
The rendered workbook inspector was visually inspected. No paid live-model batch
or desktop Excel recalculation was performed; those outcomes are not implied by
these checks.
