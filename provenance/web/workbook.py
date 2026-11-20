"""Immutable workbook snapshots, bounded cell reads, and verified edited copies."""

import datetime
import hashlib
import io
import math
import re
import zipfile
from copy import copy
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from xml.etree import ElementTree as ET

from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.workbook.properties import CalcProperties

MAX_BYTES = 5 * 1024 * 1024
MAX_INFLATED_BYTES = 25 * 1024 * 1024
MAX_ZIP_ENTRIES = 2000
MAX_SHEETS = 30
LOG_SHEET = "Provenance log"
_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
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


def saved_value(value):
    """Serialize the stored value without display rounding or time truncation."""
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return display(value)


_DECIMALS = re.compile(r"0\.(0+)")


def formatted(value, number_format):
    """Render common Excel number formats (percent, thousands, fixed decimals)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not number_format:
        return display(value)
    section = number_format.split(";")[0]
    match = _DECIMALS.search(section)
    decimals = len(match[1]) if match else 0
    if "%" in section:
        return f"{value * 100:.{decimals}f}%"
    if "#,##0" in section:
        return f"{value:,.{decimals}f}"
    if re.fullmatch(r"0(\.0+)?", section.strip()):
        return f"{value:.{decimals}f}"
    return display(value)


def _formula(value):
    text = getattr(value, "text", value)  # ArrayFormula keeps its text separately
    return text if isinstance(text, str) and text.startswith("=") else None


def _open(data, *, data_only):
    try:
        return load_workbook(io.BytesIO(data), data_only=data_only, rich_text=True)
    except (
        zipfile.BadZipFile,
        InvalidFileException,
        KeyError,
        OSError,
        ValueError,
        SyntaxError,
    ) as exc:
        raise WorkbookError("Could not read this file as an .xlsx workbook") from exc


def _inspect_archive(data):
    """Bound ZIP expansion before openpyxl parses XML; flag lossy export surfaces."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if (
                len(entries) > MAX_ZIP_ENTRIES
                or sum(i.file_size for i in entries) > MAX_INFLATED_BYTES
            ):
                raise WorkbookError("Workbook exceeds the expanded .xlsx size limit")
            names = [i.filename for i in entries]
            if len(names) != len(set(names)) or any(i.flag_bits & 1 for i in entries):
                raise WorkbookError("Workbook archive has duplicate or encrypted entries")
            if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
                raise WorkbookError("Could not read this file as an .xlsx workbook")
            content_types = archive.read("[Content_Types].xml")
            if b"macroEnabled" in content_types or any("vbaproject" in n.lower() for n in names):
                raise WorkbookError("Macro-enabled workbooks are not supported")
            risks = {
                "charts": ("xl/charts/", "xl/chartsheets/"),
                "images or drawings": ("xl/media/", "xl/drawings/drawing"),
                "pivot tables": ("xl/pivotTables/", "xl/pivotCache/"),
                "external workbook links": ("xl/externalLinks/",),
                "embedded objects or controls": ("xl/embeddings/", "xl/activeX/", "xl/ctrlProps/"),
                "data connections": ("xl/connections.xml", "xl/queryTables/"),
                "unsupported workbook metadata": (
                    "customXml/",
                    "xl/slicer",
                    "xl/timeline",
                    "xl/threadedComments/",
                    "xl/persons/",
                    "xl/metadata.xml",
                    "_xmlsignatures/",
                ),
            }
            blockers = [
                label
                for label, prefixes in risks.items()
                if any(n.startswith(prefixes) for n in names)
            ]
            # Only preserve known default metadata; functional extensions stay read-only.
            for name in names:
                if not name.endswith(".xml"):
                    continue
                xml = archive.read(name)
                if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
                    raise WorkbookError("Workbook XML declarations are not supported")
                if re.search(rb"<(?:[\w.-]+:)?extLst\b", xml):
                    root = ET.fromstring(xml)
                    if any(
                        ext not in list(root) or not _default_extension(name, ext)
                        for ext in root.iter()
                        if ext.tag.rsplit("}", 1)[-1] == "extLst"
                    ):
                        if "unsupported XML extensions" not in blockers:
                            blockers.append("unsupported XML extensions")
            return blockers
    except (zipfile.BadZipFile, KeyError, OSError, RuntimeError, ET.ParseError) as exc:
        raise WorkbookError("Could not read this file as an .xlsx workbook") from exc


def _default_extension(name, extension):
    allowed = {
        "xl/workbook.xml": {
            "{http://schemas.microsoft.com/office/spreadsheetml/2018/calcfeatures}calcFeatures"
        },
        "xl/styles.xml": {
            "{http://schemas.microsoft.com/office/spreadsheetml/2009/9/main}slicerStyles",
            "{http://schemas.microsoft.com/office/spreadsheetml/2010/11/main}timelineStyles",
        },
    }
    for item in extension:
        if len(item) != 1 or item[0].tag not in allowed.get(name, set()):
            return False
        payload = item[0]
        if payload.tag.endswith("}calcFeatures"):
            if any(
                child.tag != payload.tag.replace("calcFeatures", "feature") or len(child)
                for child in payload
            ):
                return False
        elif len(payload):
            return False
    return name in allowed


def _restore_default_extensions(original, path):
    """openpyxl drops these default hints; retain their original XML trees."""
    replacements = {}
    with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(path) as output:
        for name in ("xl/workbook.xml", "xl/styles.xml"):
            if name not in source.namelist():
                continue
            root = ET.fromstring(source.read(name))
            extension = root.find(f"{{{_MAIN_NS}}}extLst")
            if extension is not None:
                saved = ET.fromstring(output.read(name))
                saved.append(extension)
                replacements[name] = ET.tostring(saved, encoding="utf-8")
        if not replacements:
            return
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as restored:
            for entry in output.infolist():
                restored.writestr(
                    entry, replacements.get(entry.filename, output.read(entry.filename))
                )
    path.write_bytes(buffer.getvalue())


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
    export_blockers: list = field(default_factory=list)
    _formula_ranges: dict = field(repr=False, default_factory=dict)

    def _sheet(self, name):
        if name not in self._values.sheetnames or name not in [s["name"] for s in self.sheets]:
            raise WorkbookError(f"Unknown sheet: {name!r}")
        return self._values[name], self._formulas[name]

    def cell(self, sheet, row, col):
        values, formulas = self._sheet(sheet)
        source = values.cell(row, col)
        original = formulas.cell(row, col)
        is_formula = original.data_type == "f"
        reason = self._edit_block_reason(formulas, original)
        return {
            "address": format_address(row, col),
            "display": formatted(source.value, source.number_format),
            "value": saved_value(source.value),
            "formula": _formula(original.value),
            "kind": "formula" if is_formula else "blank" if original.value is None else "value",
            "value_status": ("missing_formula_cache" if source.value is None else "cached_formula")
            if is_formula
            else "saved_value",
            "editable": reason is None,
            "edit_block_reason": reason,
        }

    @cached_property
    def _array_ranges(self):
        # Snapshots are immutable; avoid scanning every populated cell for each read.
        return {
            sheet.title: [parse_range(ref) for ref in sheet.array_formulae.values()]
            for sheet in self._formulas.worksheets
        }

    def _edit_block_reason(self, sheet, cell):
        if self.export_blockers:
            return "Workbook export is blocked: " + ", ".join(self.export_blockers)
        if sheet.sheet_state != "visible":
            return "Hidden-sheet cells cannot be edited"
        if sheet.protection.sheet:
            return "Protected-sheet cells cannot be edited"
        if any(cell.coordinate in merged for merged in sheet.merged_cells.ranges):
            return "Merged cells cannot be edited"
        for table in sheet.tables.values():
            r1, c1, r2, c2 = parse_range(table.ref)
            if r1 <= cell.row <= r2 and c1 <= cell.column <= c2:
                return "Table cells cannot be edited"
        for r1, c1, r2, c2 in self._formula_ranges.get(sheet.title, []):
            if r1 <= cell.row <= r2 and c1 <= cell.column <= c2:
                return "Array or data-table formula cells cannot be edited"
        if cell.data_type == "f":
            return "Formula cells cannot be edited in the input-only workflow"
        return None

    def validate_edit_target(self, sheet, address):
        row, col, row2, col2 = parse_range(address)
        if (row, col) != (row2, col2):
            raise WorkbookError("Each change must target one cell")
        old = self.cell(sheet, row, col)
        if not old["editable"]:
            raise WorkbookError(old["edit_block_reason"])
        return old

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
            "export_blockers": self.export_blockers,
            "calculation_status": "not_recalculated",
            "export_calculation_status": "pending_excel_recalculation",
        }


def load_snapshot(data, filename):
    if not str(filename).lower().endswith(".xlsx"):
        raise WorkbookError(
            "Only .xlsx workbooks are supported (macro-enabled .xlsm and legacy .xls are not)"
        )
    if len(data) > MAX_BYTES:
        raise WorkbookError("Workbook is larger than the 5 MB limit")
    blockers = _inspect_archive(data)
    values, formulas = _open(data, data_only=True), _open(data, data_only=False)
    if len(values.worksheets) > MAX_SHEETS:
        raise WorkbookError(f"Workbook has more than {MAX_SHEETS} sheets")
    if not values.worksheets:
        raise WorkbookError("Workbook has no worksheets")
    # Inspect loaded objects too: OOXML relationships can use nonstandard part paths.
    for label, present in (
        ("charts", formulas.chartsheets or any(ws._charts for ws in formulas.worksheets)),
        ("images or drawings", any(ws._images for ws in formulas.worksheets)),
        ("pivot tables", any(ws._pivots for ws in formulas.worksheets)),
        ("external workbook links", formulas._external_links),
    ):
        if present and label not in blockers:
            blockers.append(label)
    warnings = [
        "Formula values are saved caches, not recalculated results. Edited copies require Excel recalculation."
    ]
    if blockers:
        warnings.append("Edited-copy export is blocked to preserve: " + ", ".join(blockers) + ".")
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
        export_blockers=blockers,
        _values=values,
        _formulas=formulas,
        _formula_ranges={
            ws.title: [
                parse_range(cell.value.ref)
                for cell in ws._cells.values()
                if cell.data_type == "f" and getattr(cell.value, "ref", None)
            ]
            for ws in formulas.worksheets
        },
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
    if snapshot.export_blockers:
        raise WorkbookError("Workbook export is blocked: " + ", ".join(snapshot.export_blockers))
    targets = set()
    for change in changes:
        old = snapshot.validate_edit_target(change["sheet"], change["cell"])
        key = (change["sheet"], old["address"])
        if key in targets:
            raise WorkbookError(f"Duplicate edit target: {key[0]}!{key[1]}")
        targets.add(key)
        for key_name, expected in (
            ("old_display", old["display"]),
            ("old_formula", old["formula"]),
            ("old_value", old["value"]),
        ):
            if key_name in change and change[key_name] != expected:
                raise WorkbookError(f"Edit precondition failed at {key[0]}!{key[1]}: {key_name}")
        content = change["new_content"]
        if isinstance(content, str) and content.lstrip().startswith("="):
            raise WorkbookError("New formulas are not supported in the input-only workflow")
        if isinstance(content, bool) or not isinstance(content, (str, int, float)):
            raise WorkbookError("New content must be a number or text")
        if isinstance(content, float) and not math.isfinite(content):
            raise WorkbookError("New content must be finite")
        if isinstance(content, str) and (not content or len(content) > 32767):
            raise WorkbookError("New text must contain 1–32767 characters")
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
        if isinstance(change["new_content"], str):
            target.data_type = "s"
        sources = _source_text(change)
        generated = change.get("generated_by") or "Agent proposal"
        note = f"Provenance ({generated}): {change['rationale']}\nSource: {sources}"
        if target.comment:
            comment = copy(target.comment)
            comment.text += "\n\n" + note
        else:
            comment = Comment(note, "Provenance")
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
                generated,
                snapshot.sha256,
                approved_at,
            ]
        )
    name = LOG_SHEET
    suffix = 2
    existing_names = {title.casefold() for title in book.sheetnames}
    while name.casefold() in existing_names:
        name = f"{LOG_SHEET} {suffix}"
        suffix += 1
    log = book.create_sheet(name)
    log.append(
        [
            "Cell",
            "Old value",
            "Old formula",
            "New value or formula",
            "Rationale",
            "Sources",
            "Generated by",
            "Original snapshot SHA-256",
            "Approved at",
        ]
    )
    for line in rows:
        log.append(line)
    for row in log:
        for cell in row:
            if isinstance(cell.value, str):
                cell.data_type = "s"
    book.calculation = book.calculation or CalcProperties()
    book.calculation.calcMode = "auto"
    book.calculation.fullCalcOnLoad = True
    book.calculation.forceFullCalc = True
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(snapshot.filename).stem
    number = 1
    while (out_dir / f"{stem}-provenance-{number}.xlsx").exists():
        number += 1
    path = out_dir / f"{stem}-provenance-{number}.xlsx"
    try:
        book.save(path)
        _restore_default_extensions(snapshot.data, path)
        check = load_workbook(path, rich_text=True)
        for change in changes:
            row, col, _, _ = parse_range(change["cell"])
            if check[change["sheet"]].cell(row, col).value != change["new_content"]:
                raise WorkbookError(f"Export verification failed at {change['cell']}")
        if check[name].max_row != len(changes) + 1:
            raise WorkbookError("Export verification failed: provenance log incomplete")
        _verify_preservation(snapshot._formulas, book, check, targets, name)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def _cell_content(cell):
    value = cell.value
    if cell.data_type == "f" and not isinstance(value, str):
        value = vars(value)
    return value, cell.data_type


def _verify_preservation(original, edited, check, targets, log_name):
    """Verify stored content and supported presentation, never calculated results."""
    if check.sheetnames != original.sheetnames + [log_name]:
        raise WorkbookError("Export verification failed: sheet structure changed")
    for before in original.worksheets:
        after = check[before.title]
        if before.sheet_state != after.sheet_state or set(before.merged_cells.ranges) != set(
            after.merged_cells.ranges
        ):
            raise WorkbookError("Export verification failed: sheet layout changed")
        for position in before._cells.keys() | after._cells.keys():
            old, new = before.cell(*position), after.cell(*position)
            expected = edited[before.title].cell(*position)
            if (before.title, old.coordinate) not in targets and _cell_content(
                old
            ) != _cell_content(new):
                raise WorkbookError(
                    f"Export verification failed: non-target content changed at {before.title}!{old.coordinate}"
                )
            if old._style != new._style or old.hyperlink != new.hyperlink:
                raise WorkbookError(
                    f"Export verification failed: cell formatting changed at {old.coordinate}"
                )
            if expected.comment != new.comment:
                raise WorkbookError(
                    f"Export verification failed: comment changed at {old.coordinate}"
                )
    for row in edited[log_name]:
        for expected in row:
            actual = check[log_name][expected.coordinate]
            # Excel serializes empty strings as empty cells.
            if (expected.value or None) != actual.value or actual.data_type == "f":
                raise WorkbookError("Export verification failed: provenance log content changed")
    if (
        check.calculation.calcMode != "auto"
        or not check.calculation.fullCalcOnLoad
        or not check.calculation.forceFullCalc
    ):
        raise WorkbookError("Export verification failed: recalculation was not requested")
