import { useEffect, useMemo, useRef, useState } from "react";
import { getGrid } from "../api";
import { columnLetter, parseCellLocator, rangeLabel, type CellRange } from "../format";
import type { Citation, Grid, Session } from "../types";

type Props = {
  session: Session;
  highlight: Citation | null;
  busy: boolean;
  onUpload: (file: File) => Promise<void>;
  onUseDemo: () => Promise<void>;
  onSetContext: (sheet: string, range: string) => Promise<void>;
  onClearContext: () => Promise<void>;
};

type Point = { r: number; c: number };

export function WorkbookPanel({ session, highlight, busy, onUpload, onUseDemo, onSetContext, onClearContext }: Props) {
  const workbook = session.workbook;
  const [sheet, setSheet] = useState<string>("");
  const [grid, setGrid] = useState<Grid | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [anchor, setAnchor] = useState<Point | null>(null);
  const [focus, setFocus] = useState<Point | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const cited: CellRange | null = useMemo(
    () => (highlight ? parseCellLocator(highlight.locator) : null),
    [highlight],
  );

  useEffect(() => {
    if (!workbook) return;
    const preferred = cited?.sheet || session.context?.sheet || workbook.sheets[0]?.name || "";
    setSheet((current) => (cited?.sheet ? cited.sheet : workbook.sheets.some((s) => s.name === current) ? current : preferred));
  }, [workbook?.snapshot_id, cited?.sheet]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!workbook || !sheet) return;
    setError(null);
    getGrid(session.id, sheet)
      .then(setGrid)
      .catch((err: Error) => setError(err.message));
    setAnchor(null);
    setFocus(null);
  }, [session.id, workbook?.snapshot_id, sheet]); // eslint-disable-line react-hooks/exhaustive-deps

  const upload = async (file: File | undefined) => {
    if (!file) return;
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
            <button
              type="button"
              disabled={uploading || busy}
              onClick={() => {
                setUploading(true);
                onUseDemo()
                  .catch((err: Error) => setError(err.message))
                  .finally(() => setUploading(false));
              }}
              className="rounded-md border border-rule px-3 py-1.5 text-sm hover:border-ink-faint disabled:opacity-40"
            >
              Use the demo Cloudflare model
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

  const choose = (point: Point, extend: boolean) => {
    if (extend && anchor) setFocus(point);
    else {
      setAnchor(point);
      setFocus(point);
    }
  };

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
              onClick={() => setSheet(s.name)}
              className={`rounded px-2 py-0.5 text-sm ${s.name === sheet ? "bg-ink text-white" : "text-ink-soft hover:bg-chrome"}`}
            >
              {s.name}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-rule bg-surface px-5 py-2 text-sm">
        {selectionLabel ? (
          <>
            <span>
              Selected <span className="tabular font-medium">{sheet}!{selectionLabel}</span>
              <span className="text-ink-faint"> ({cellCount} {cellCount === 1 ? "cell" : "cells"})</span>
            </span>
            <button
              type="button"
              disabled={busy || cellCount > 400}
              onClick={() => onSetContext(sheet, selectionLabel).catch((err: Error) => setError(err.message))}
              className="rounded-md bg-ink px-2.5 py-1 text-white disabled:opacity-40"
            >
              Attach to next question
            </button>
            {cellCount > 400 && <span className="text-rust">Select 400 cells or fewer</span>}
          </>
        ) : (
          <span className="text-ink-faint">Click a cell, or drag or Shift+click to select a range to attach to your question.</span>
        )}
        {session.context && (
          <span className="ml-auto flex items-center gap-2">
            <span className="rounded border border-highlight bg-highlight-soft px-1.5 py-0.5 text-xs">
              Attached {session.context.sheet}!{session.context.range}
            </span>
            <button type="button" className="text-xs text-ink-faint underline" onClick={() => void onClearContext()}>
              Remove
            </button>
          </span>
        )}
      </div>
      {error && <p role="alert" className="px-5 py-2 text-sm text-rust">{error}</p>}

      <div className="min-h-0 flex-1 overflow-auto bg-surface">
        {grid && (
          <table className="tabular border-collapse text-[13px] select-none" aria-label={`Sheet ${sheet}`}>
            <thead>
              <tr>
                <th className="sticky top-0 left-0 z-20 h-6 w-10 border border-rule bg-chrome" />
                {Array.from({ length: columns }, (_, index) => (
                  <th key={index} className="sticky top-0 z-10 min-w-[72px] border border-rule bg-chrome px-1 font-normal text-ink-faint">
                    {columnLetter(index + 1)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {grid.rows.map((row, rowIndex) => {
                const r = rowIndex + 1;
                return (
                  <tr key={r}>
                    <th className="sticky left-0 z-10 border border-rule bg-chrome px-1 text-right font-normal text-ink-faint">{r}</th>
                    {Array.from({ length: columns }, (_, colIndex) => {
                      const c = colIndex + 1;
                      const cell = row[colIndex] ?? null;
                      const isCited = !!cited && cited.sheet === sheet && inRange(cited, r, c);
                      const isSelected = inRange(selection, r, c);
                      const isContext = inRange(contextRange, r, c);
                      const numeric = cell && /^-?[\d.,]+%?$/.test(cell.display);
                      return (
                        <td
                          key={c}
                          title={cell?.formula ? `${cell.address}: ${cell.formula}` : cell ? cell.address : `${columnLetter(c)}${r}`}
                          onMouseDown={(event) => {
                            setDragging(true);
                            choose({ r, c }, event.shiftKey);
                          }}
                          onMouseEnter={() => dragging && setFocus({ r, c })}
                          className={`max-w-[360px] cursor-cell truncate border border-rule px-1.5 py-0.5 ${
                            numeric ? "text-right" : ""
                          } ${isCited ? "bg-highlight outline-2 -outline-offset-2 outline-ledger" : isSelected ? "bg-ledger-soft" : isContext ? "bg-highlight-soft" : ""} ${
                            cell?.formula ? "text-ledger" : ""
                          }`}
                        >
                          {cell?.display ?? ""}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        {grid && (grid.max_row > grid.rows.length || grid.max_col > columns) && (
          <p className="px-5 py-2 text-xs text-ink-faint">
            Showing the first {grid.rows.length} rows and {columns} columns of {grid.max_row} × {grid.max_col}. The agent can read any range.
          </p>
        )}
      </div>
      <p className="border-t border-rule bg-surface px-5 py-1.5 text-xs text-ink-faint">
        Green text marks formula cells; values shown are those saved in the file.
      </p>
    </div>
  );
}
