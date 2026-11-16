"""Immutable workbook snapshots, bounded cell reads, and verified edited copies."""

import datetime
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException

MAX_BYTES = 5 * 1024 * 1024
MAX_SHEETS = 30
LOG_SHEET = "Provenance log"
_CELL = re.compile(r"\$?([A-Za-z]{1,3})\$?(\d{1,7})")


class WorkbookError(ValueError):
    """User-facing workbook problem; the message is safe to show."""


def _column_number(letters):
    number = 0
    for letter in letters.upper():
        number = number * 26 + ord(letter) - 64
    return number


def parse_range(text):
    """Return (min_row, min_col, max_row, max_col) for A1 or A1:C3 notation."""
    parts = text.strip().split(":") if isinstance(text, str) else []
    if not 1 <= len(parts) <= 2:
        raise WorkbookError(f"Invalid cell range: {text!r}")
    points = []
    for part in parts:
        match = _CELL.fullmatch(part.strip())
        if not match or int(match[2]) < 1:
            raise WorkbookError(f"Invalid cell range: {text!r}")
        points.append((int(match[2]), _column_number(match[1])))
    (row1, col1), (row2, col2) = points[0], points[-1]
    if row2 < row1 or col2 < col1 or col2 > 16384 or row2 > 1048576:
        raise WorkbookError(f"Invalid cell range: {text!r}")
    return row1, col1, row2, col2


def format_address(row, col):
    return f"{get_column_letter(col)}{row}"


def display(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.10g}"
    if isinstance(value, (datetime.datetime, datetime.date)):
        return (
            value.date().isoformat() if isinstance(value, datetime.datetime) else value.isoformat()
        )
    return str(value)


def _formula(value):
    text = getattr(value, "text", value)  # ArrayFormula keeps its text separately
    return text if isinstance(text, str) and text.startswith("=") else None


def _open(data, *, data_only):
    try:
        return load_workbook(io.BytesIO(data), data_only=data_only)
    except (zipfile.BadZipFile, InvalidFileException, KeyError, OSError, ValueError) as exc:
        raise WorkbookError("Could not read this file as an .xlsx workbook") from exc


@dataclass
class Snapshot:
    snapshot_id: str
    sha256: str
    filename: str
    data: bytes
    sheets: list
    warnings: list
    _values: object = field(repr=False, default=None)
    _formulas: object = field(repr=False, default=None)

    def _sheet(self, name):
        if name not in self._values.sheetnames or name not in [s["name"] for s in self.sheets]:
            raise WorkbookError(f"Unknown sheet: {name!r}")
        return self._values[name], self._formulas[name]

    def cell(self, sheet, row, col):
        values, formulas = self._sheet(sheet)
        return {
            "address": format_address(row, col),
            "display": display(values.cell(row, col).value),
            "formula": _formula(formulas.cell(row, col).value),
        }

    def cells(self, sheet, rng, limit):
        self._sheet(sheet)
        row1, col1, row2, col2 = parse_range(rng)
        count = (row2 - row1 + 1) * (col2 - col1 + 1)
        if count > limit:
            raise WorkbookError(f"Range has {count} cells; the limit is {limit}")
        return [
            self.cell(sheet, row, col)
            for row in range(row1, row2 + 1)
            for col in range(col1, col2 + 1)
        ]

    def grid(self, sheet, rows=60, cols=26):
        values, _ = self._sheet(sheet)
        max_row, max_col = values.max_row or 1, values.max_column or 1
        grid_rows = []
        for row in range(1, min(max_row, rows) + 1):
            line = []
            for col in range(1, min(max_col, cols) + 1):
                cell = self.cell(sheet, row, col)
                line.append(cell if cell["display"] or cell["formula"] else None)
            grid_rows.append(line)
        return {"sheet": sheet, "max_row": max_row, "max_col": max_col, "rows": grid_rows}

    def info(self):
        return {
            "snapshot_id": self.snapshot_id,
            "filename": self.filename,
            "sha256": self.sha256,
            "sheets": self.sheets,
            "warnings": self.warnings,
        }


def load_snapshot(data, filename):
    if not str(filename).lower().endswith(".xlsx"):
        raise WorkbookError(
            "Only .xlsx workbooks are supported (macro-enabled .xlsm and legacy .xls are not)"
        )
    if len(data) > MAX_BYTES:
        raise WorkbookError("Workbook is larger than the 5 MB limit")
    values, formulas = _open(data, data_only=True), _open(data, data_only=False)
    if len(values.worksheets) > MAX_SHEETS:
        raise WorkbookError(f"Workbook has more than {MAX_SHEETS} sheets")
    if not values.worksheets:
        raise WorkbookError("Workbook has no worksheets")
    warnings = []
    if values.chartsheets:
        warnings.append("Chart sheets are not shown and will not be kept in the edited copy.")
    if any(
        getattr(ws, "_charts", None) or getattr(ws, "_images", None) for ws in values.worksheets
    ):
        warnings.append("Charts or images may not be preserved in the edited copy.")
    if any(getattr(ws, "_pivots", None) for ws in formulas.worksheets):
        warnings.append("Pivot tables are read as values and may not refresh in the edited copy.")
    digest = hashlib.sha256(data).hexdigest()
    return Snapshot(
        snapshot_id=digest[:12],
        sha256=digest,
        filename=Path(str(filename)).name,
        data=bytes(data),
        sheets=[
            {"name": ws.title, "max_row": ws.max_row or 1, "max_col": ws.max_column or 1}
            for ws in values.worksheets
        ],
        warnings=warnings,
        _values=values,
        _formulas=formulas,
    )


def _source_text(change):
    titles = change.get("source_titles") or {}
    return "; ".join(
        f'{titles.get(c["source_id"], c["source_id"])} {c["locator"]}: "{c["quote"]}"'
        for c in change.get("citations", [])
    )


def export_copy(snapshot, changes, out_dir, *, approved_at):
    """Write a separate edited copy with comments and a provenance log; verify it."""
    if not changes:
        raise WorkbookError("No approved changes to export")
    book = _open(snapshot.data, data_only=False)
    rows = []
    for change in changes:
        if change["sheet"] not in book.sheetnames:
            raise WorkbookError(f"Unknown sheet: {change['sheet']!r}")
        row, col, row2, col2 = parse_range(change["cell"])
        if (row, col) != (row2, col2):
            raise WorkbookError("Each change must target one cell")
        old = snapshot.cell(change["sheet"], row, col)
        target = book[change["sheet"]].cell(row, col)
        target.value = change["new_content"]
        sources = _source_text(change)
        comment = Comment(f"Provenance: {change['rationale']}\nSource: {sources}", "Provenance")
        comment.width, comment.height = 320, 140
        target.comment = comment
        rows.append(
            [
                f"{change['sheet']}!{old['address']}",
                old["display"],
                old["formula"] or "",
                display(change["new_content"]),
                change["rationale"],
                sources,
                snapshot.sha256,
                approved_at,
            ]
        )
    name = LOG_SHEET
    while name in book.sheetnames:
        name += " +"
    log = book.create_sheet(name)
    log.append(
        [
            "Cell",
            "Old value",
            "Old formula",
            "New value or formula",
            "Rationale",
            "Sources",
            "Original snapshot SHA-256",
            "Approved at",
        ]
    )
    for line in rows:
        log.append(line)
    book.calculation.fullCalcOnLoad = True
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(snapshot.filename).stem
    number = 1
    while (out_dir / f"{stem}-provenance-{number}.xlsx").exists():
        number += 1
    path = out_dir / f"{stem}-provenance-{number}.xlsx"
    book.save(path)
    try:
        check = load_workbook(path)
        for change in changes:
            row, col, _, _ = parse_range(change["cell"])
            if check[change["sheet"]].cell(row, col).value != change["new_content"]:
                raise WorkbookError(f"Export verification failed at {change['cell']}")
        if check[name].max_row != len(changes) + 1:
            raise WorkbookError("Export verification failed: provenance log incomplete")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path
