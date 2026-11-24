import { useEffect, useMemo, useRef, useState } from "react";
import { getGrid } from "../api";
import { columnLetter, parseCellLocator, rangeLabel, type CellRange } from "../format";
import { inExcelPane } from "../excel";
import type { Citation, Grid, Session } from "../types";

type Props = {
  session: Session;
  highlight: Citation | null;
  busy: boolean;
  onUpload: (file: File) => Promise<void>;
  onSetContext: (sheet: string, range: string) => Promise<void>;
  onClearContext: () => Promise<void>;
};

type Point = { r: number; c: number };

export function WorkbookPanel({ session, highlight, busy, onUpload, onSetContext, onClearContext }: Props) {
  const workbook = session.workbook;
  const [sheet, setSheet] = useState<string>("");
  const [grid, setGrid] = useState<Grid | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [anchor, setAnchor] = useState<Point | null>(null);
  const [focus, setFocus] = useState<Point | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [origin, setOrigin] = useState<Point>({ r: 1, c: 1 });
  const [rangeInput, setRangeInput] = useState("");
  const staleCitation = !!highlight && highlight.source_id !== `workbook:${workbook?.snapshot_id}`;
  const input = useRef<HTMLInputElement>(null);

  const cited: CellRange | null = useMemo(
    () => (highlight && !staleCitation ? parseCellLocator(highlight.locator) : null),
    [highlight, staleCitation],
  );

  useEffect(() => {
    const attached = session.context ? parseCellLocator(session.context.range, session.context.sheet) : null;
    setSheet(attached?.sheet || workbook?.sheets[0]?.name || "");
    setOrigin({ r: attached?.r1 || 1, c: attached?.c1 || 1 });
    setAnchor(attached ? { r: attached.r1, c: attached.c1 } : null);
    setFocus(attached ? { r: attached.r2, c: attached.c2 } : null);
    setRangeInput(attached ? rangeLabel(attached) : "");
  }, [session.id, workbook?.snapshot_id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!cited) return;
    setSheet(cited.sheet);
    setOrigin({ r: cited.r1, c: cited.c1 });
    setAnchor({ r: cited.r1, c: cited.c1 });
    setFocus({ r: cited.r2, c: cited.c2 });
    setRangeInput(rangeLabel(cited));
  }, [cited]);

  useEffect(() => {
    if (!workbook || !sheet) return;
    let active = true;
    setError(null);
    setGrid(null);
    setLoading(true);
    getGrid(session.id, sheet, origin.r, origin.c)
      .then((result) => {
        if (!active) return;
        if (result.snapshot_id !== workbook.snapshot_id) {
          setError("The workbook changed while loading. Reopen the Workbook tab to load the current snapshot.");
          return;
        }
        setGrid(result);
      })
      .catch((err: Error) => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [session.id, workbook?.snapshot_id, sheet, origin.r, origin.c]);

  const upload = async (file: File | undefined) => {
    if (!file || busy || uploading) return;
    setUploading(true);
    setError(null);
    try {
      await onUpload(file);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
      if (input.current) input.current.value = "";
    }
  };

  const fileInput = (
    <input
      ref={input}
      type="file"
      accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      className="sr-only"
      aria-label="Upload an .xlsx workbook"
      onChange={(event) => void upload(event.target.files?.[0])}
    />
  );

  if (!workbook) {
    return (
      <div className="p-6">
        <div
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            void upload(event.dataTransfer.files?.[0]);
          }}
          className="rounded-lg border-2 border-dashed border-rule bg-surface px-6 py-10 text-center"
        >
          <p className="font-medium">Bring your model</p>
          <p className="mx-auto mt-1 max-w-[46ch] text-sm text-ink-soft">
            Upload an .xlsx file (up to 5 MB). The agent reads it as an unchangeable snapshot; any edit it suggests
            waits for your approval and goes into a separate copy.
          </p>
          <div className="mt-4 flex justify-center gap-2">
            <button
              type="button"
              disabled={uploading || busy}
              onClick={() => input.current?.click()}
              className="rounded-md bg-ink px-3 py-1.5 text-sm text-white disabled:opacity-40"
            >
              {uploading ? "Reading workbook" : "Choose file"}
            </button>

          </div>
          {fileInput}
          {error && <p role="alert" className="mt-3 text-sm text-rust">{error}</p>}
        </div>
      </div>
    );
  }

  const selection =
    anchor && focus
      ? { r1: Math.min(anchor.r, focus.r), c1: Math.min(anchor.c, focus.c), r2: Math.max(anchor.r, focus.r), c2: Math.max(anchor.c, focus.c) }
      : null;
  const selectionLabel = selection ? rangeLabel(selection) : null;
  const cellCount = selection ? (selection.r2 - selection.r1 + 1) * (selection.c2 - selection.c1 + 1) : 0;
  const inRange = (range: { r1: number; c1: number; r2: number; c2: number } | null, r: number, c: number) =>
    !!range && r >= range.r1 && r <= range.r2 && c >= range.c1 && c <= range.c2;
  const contextRange =
    session.context && session.context.sheet === sheet ? parseCellLocator(session.context.range, sheet) : null;
  const columns = grid ? Math.max(...grid.rows.map((row) => row.length), 1) : 0;

  const selectRange = (start: Point, end: Point) => {
    if (busy) return;
    setAnchor(start);
    setFocus(end);
    const range = rangeLabel({
      r1: Math.min(start.r, end.r), c1: Math.min(start.c, end.c),
      r2: Math.max(start.r, end.r), c2: Math.max(start.c, end.c),
    });
    void onSetContext(sheet, range).catch((err: Error) => setError(err.message));
  };
  const choose = (point: Point, extend: boolean) => {
    selectRange(extend && anchor ? anchor : point, point);
  };

  const navigate = (r: number, c: number) => {
    setOrigin({ r, c });
    setAnchor(null);
    setFocus(null);
    setRangeInput("");
  };
  const jump = () => {
    const range = parseCellLocator(rangeInput, sheet);
    if (!range || range.sheet !== sheet || range.r2 - range.r1 >= 60 || range.c2 - range.c1 >= 26) {
      setError("Enter a valid range on this sheet, at most 60 rows by 26 columns (for example AA70:AC75).");
      return;
    }
    setError(null);
    setOrigin({ r: range.r1, c: range.c1 });
    selectRange({ r: range.r1, c: range.c1 }, { r: range.r2, c: range.c2 });
  };
  const inspected = focus && grid
    ? grid.rows[focus.r - grid.start_row]?.[focus.c - grid.start_col]
    : null;

  return (
    <div className="flex h-full flex-col" onMouseUp={() => setDragging(false)}>
      <div className="border-b border-rule bg-surface px-5 py-3">
        <div className="flex flex-wrap items-baseline gap-x-3">
          <p className="font-medium">{workbook.filename}</p>
          <p className="tabular text-xs text-ink-faint" title={workbook.sha256}>
            Snapshot {workbook.snapshot_id}
          </p>
          <button
            type="button"
            disabled={busy || uploading}
            onClick={() => input.current?.click()}
            className="ml-auto text-sm text-ledger underline disabled:opacity-40"
            title="Uploading a new file marks pending proposals as stale"
          >
            Upload a different file
          </button>
          {fileInput}
        </div>
        <p className="mt-1 text-xs text-ink-soft">Uploaded snapshot · input edits only · no browser recalculation</p>
        {workbook.export_blockers?.length > 0 && (
          <div role="status" className="mt-2 rounded border border-rust/30 bg-rust-soft p-2 text-sm text-rust">
            <p className="font-medium">Read-only workbook — edited copies unavailable</p>
            {workbook.export_blockers.map((reason) => <p key={reason}>{reason}</p>)}
          </div>
        )}
        {workbook.warnings.map((warning) => (
          <p key={warning} className="mt-1 text-xs text-rust">
            {warning}
          </p>
        ))}
        <div role="tablist" aria-label="Sheets" className="mt-2 flex flex-wrap gap-1">
          {workbook.sheets.map((s) => (
            <button
              key={s.name}
              role="tab"
              aria-selected={s.name === sheet}
              type="button"
              onClick={() => { setSheet(s.name); navigate(1, 1); }}
              className={`rounded px-2 py-0.5 text-sm ${s.name === sheet ? "bg-ink text-white" : "text-ink-soft hover:bg-chrome"}`}
            >
              {s.name}
            </button>
          ))}
        </div>
      </div>

      {staleCitation && <p role="status" className="px-5 py-2 text-sm text-rust">This citation belongs to a previous upload. It cannot be located in the current workbook.</p>}
      <form onSubmit={(event) => { event.preventDefault(); jump(); }} className="flex flex-wrap items-center gap-2 border-b border-rule px-5 py-2 text-sm">
        <label htmlFor="workbook-range">Go to range</label>
        <input id="workbook-range" value={rangeInput} onChange={(event) => setRangeInput(event.target.value)} placeholder="A1 or AA70:AC75" className="w-40 rounded border border-rule px-2 py-1" />
        <button type="submit" className="rounded border border-rule px-3 py-1">Go</button>
      </form>
      <div className="flex flex-wrap items-center gap-2 border-b border-rule bg-surface px-5 py-2 text-sm">
        {selectionLabel ? (
          <>
            <span>
              Selected <span className="tabular font-medium">{sheet}!{selectionLabel}</span>
              <span className="text-ink-faint"> ({cellCount} {cellCount === 1 ? "cell" : "cells"})</span>
            </span>
            {cellCount > 400 && <span className="text-rust">Select 400 cells or fewer before asking</span>}
          </>
        ) : (
          <span className="text-ink-faint">Click a cell, or drag or Shift+click to select a range. {inExcelPane ? "Select cells in Excel to focus your next question." : "Your selection is included automatically with your next question."}</span>
        )}
        {session.context && (
          <span className="ml-auto flex items-center gap-2">
            <span className="rounded border border-highlight bg-highlight-soft px-1.5 py-0.5 text-xs">
              Attached {session.context.sheet}!{session.context.range}
            </span>
            <button type="button" className="text-xs text-ink-faint underline" disabled={busy} onClick={() => onClearContext().catch((err: Error) => setError(err.message))}>
              Remove
            </button>
          </span>
        )}
      </div>
      {error && <p role="alert" className="px-5 py-2 text-sm text-rust">{error}</p>}

      {inspected && (
        <div aria-label="Cell details" className="border-b border-rule bg-chrome px-5 py-2 text-sm break-words">
          <p className="font-medium">{sheet}!{inspected.address} · {inspected.kind === "formula" ? "Formula" : inspected.kind === "blank" ? "Blank cell" : "Input value"}</p>
          {inspected.formula && <p className="font-mono text-xs">{inspected.formula}</p>}
          <p>Saved value: {inspected.value_status === "missing_formula_cache" ? "Unavailable — open and save in Excel to calculate" : inspected.value || "Empty"}</p>
          {inspected.value_status === "cached_formula" && <p className="text-xs text-ink-soft">Cached formula result; not recalculated in the browser.</p>}
          <p className="text-xs text-ink-soft">{inspected.editable ? "Eligible for an approved input update." : inspected.edit_block_reason}</p>
        </div>
      )}
      <div className="flex flex-wrap gap-2 border-b border-rule px-5 py-1.5 text-xs" aria-label="Workbook navigation">
        <button type="button" disabled={origin.r === 1 || loading} onClick={() => navigate(Math.max(1, origin.r - 60), origin.c)} className="rounded border border-rule px-2 py-1 disabled:opacity-40">Previous rows</button>
        <button type="button" disabled={!grid || origin.r + 60 > grid.max_row || loading} onClick={() => navigate(origin.r + 60, origin.c)} className="rounded border border-rule px-2 py-1 disabled:opacity-40">Next rows</button>
        <button type="button" disabled={origin.c === 1 || loading} onClick={() => navigate(origin.r, Math.max(1, origin.c - 26))} className="rounded border border-rule px-2 py-1 disabled:opacity-40">Previous columns</button>
        <button type="button" disabled={!grid || origin.c + 26 > grid.max_col || loading} onClick={() => navigate(origin.r, origin.c + 26)} className="rounded border border-rule px-2 py-1 disabled:opacity-40">Next columns</button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto bg-surface" aria-busy={loading}>
        {loading && <p role="status" className="px-5 py-3 text-sm text-ink-soft">Loading workbook range…</p>}
        {grid && (
          <table className="tabular border-collapse text-[13px] select-none" aria-label={`Sheet ${sheet}`}>
            <thead>
              <tr>
                <th className="sticky top-0 left-0 z-20 h-6 w-10 border border-rule bg-chrome" />
                {Array.from({ length: columns }, (_, index) => (
                  <th key={index} className="sticky top-0 z-10 min-w-[72px] border border-rule bg-chrome px-1 font-normal text-ink-faint">
                    {columnLetter(grid.start_col + index)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {grid.rows.map((row, rowIndex) => {
                const r = grid.start_row + rowIndex;
                return (
                  <tr key={r}>
                    <th className="sticky left-0 z-10 border border-rule bg-chrome px-1 text-right font-normal text-ink-faint">{r}</th>
                    {Array.from({ length: columns }, (_, colIndex) => {
                      const c = grid.start_col + colIndex;
                      const cell = row[colIndex] ?? null;
                      const isCited = !!cited && cited.sheet === sheet && inRange(cited, r, c);
                      const isSelected = inRange(selection, r, c);
                      const isContext = inRange(contextRange, r, c);
                      const numeric = cell && /^-?[\d.,]+%?$/.test(cell.display);
                      return (
                        <td
                          key={c}
                          title={cell?.formula ? `${cell.address}: ${cell.formula}` : cell ? cell.address : `${columnLetter(c)}${r}`}
                          tabIndex={(focus ? focus.r === r && focus.c === c : rowIndex === 0 && colIndex === 0) ? 0 : -1}
                          aria-label={`${columnLetter(c)}${r}${cell?.formula ? ", formula" : ""}: ${cell?.display || "empty"}`}
                          onKeyDown={(event) => {
                            if (["Enter", " "].includes(event.key)) {
                              event.preventDefault(); choose({ r, c }, event.shiftKey); return;
                            }
                            const offsets: Record<string, Point> = { ArrowUp: { r: -1, c: 0 }, ArrowDown: { r: 1, c: 0 }, ArrowLeft: { r: 0, c: -1 }, ArrowRight: { r: 0, c: 1 } };
                            const offset = offsets[event.key];
                            if (!offset) return;
                            event.preventDefault();
                            const next = { r: r + offset.r, c: c + offset.c };
                            if (next.r < grid.start_row || next.r >= grid.start_row + grid.rows.length || next.c < grid.start_col || next.c >= grid.start_col + columns) return;
                            selectRange(event.shiftKey ? anchor ?? { r, c } : next, next);
                            event.currentTarget.closest("table")?.querySelector<HTMLElement>(`[data-cell="${columnLetter(next.c)}${next.r}"]`)?.focus();
                          }}
                          data-cell={`${columnLetter(c)}${r}`}
                          onMouseDown={(event) => {
                            event.currentTarget.focus();
                            setDragging(true);
                            choose({ r, c }, event.shiftKey);
                          }}
                          onMouseEnter={(event) => {
                            if (!event.buttons) setDragging(false);
                            else if (dragging) choose({ r, c }, true);
                          }}
                          className={`max-w-[360px] cursor-cell truncate border border-rule px-1.5 py-0.5 ${
                            numeric ? "text-right" : ""
                          } ${isCited ? "bg-highlight outline-2 -outline-offset-2 outline-ledger" : isSelected ? "bg-ledger-soft" : isContext ? "bg-highlight-soft" : ""} ${
                            cell?.formula ? "text-ledger" : ""
                          }`}
                        >
                          {cell?.value_status === "missing_formula_cache" ? "Not calculated" : cell?.display ?? ""}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        {grid && <p className="px-5 py-2 text-xs text-ink-faint">Showing {columnLetter(grid.start_col)}{grid.start_row}:{columnLetter(grid.start_col + columns - 1)}{grid.start_row + grid.rows.length - 1}. Worksheet extent: {grid.max_row} rows × {grid.max_col} columns.</p>}
      </div>
      <p className="border-t border-rule bg-surface px-5 py-1.5 text-xs text-ink-faint">
        Values are from the uploaded file. Downloaded changes appear here only after you upload the edited copy. Use arrow keys to navigate cells; Shift extends selection.
      </p>
    </div>
  );
}
