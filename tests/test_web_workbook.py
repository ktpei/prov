import datetime
import hashlib
import io
import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart
from openpyxl.comments import Comment
from openpyxl.styles import Font
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.worksheet.table import Table

from provenance.web.workbook import WorkbookError, export_copy, load_snapshot, parse_range

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "data/demo/cloudflare-fy2024-model.xlsx"


def fixture():
    return load_snapshot(FIXTURE.read_bytes(), FIXTURE.name)


def change(cell, new_content, title="Cloudflare Q3 2024 release"):
    return {
        "sheet": "Model",
        "cell": cell,
        "new_content": new_content,
        "rationale": "Align with management guidance",
        "citations": [
            {
                "source_id": "cloudflare-q3-2024-release",
                "locator": "L63",
                "quote": "Total revenue of $1,661.0 to $1,662.0 million",
            }
        ],
        "source_titles": {"cloudflare-q3-2024-release": title},
    }


class ParseRangeTests(unittest.TestCase):
    def test_parse_range_variants(self):
        self.assertEqual(parse_range("B5"), (5, 2, 5, 2))
        self.assertEqual(parse_range("$A$1:C3"), (1, 1, 3, 3))
        self.assertEqual(parse_range("aa10"), (10, 27, 10, 27))
        for bad in ("5B", "A0", "C3:A1", "", "A1:B2:C3"):
            with self.assertRaises(WorkbookError, msg=bad):
                parse_range(bad)


class SnapshotTests(unittest.TestCase):
    def test_fixture_snapshot(self):
        snapshot = fixture()
        digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        self.assertEqual(snapshot.sha256, digest)
        self.assertEqual(snapshot.snapshot_id, digest[:12])
        self.assertIn("Model", [sheet["name"] for sheet in snapshot.sheets])
        cells = snapshot.cells("Model", "B7:B9", 200)
        self.assertEqual([cell["address"] for cell in cells], ["B7", "B8", "B9"])
        self.assertEqual([cell["display"] for cell in cells], ["1,650.0", "215.0", "13.0%"])
        self.assertEqual([cell["value"] for cell in cells], ["1650", "215", "0.1303030303030303"])
        self.assertIsNone(cells[0]["formula"])
        self.assertEqual(cells[2]["formula"], "=B8/B7")

    def test_grid_shape(self):
        grid = fixture().grid("Model")
        self.assertEqual(grid["sheet"], "Model")
        self.assertEqual(grid["rows"][6][1]["display"], "1,650.0")
        self.assertEqual(grid["rows"][6][1]["address"], "B7")
        self.assertLessEqual(len(grid["rows"]), 60)
        with self.assertRaises(WorkbookError):
            fixture().grid("Missing")

    def test_rejects_non_xlsx(self):
        with self.assertRaises(WorkbookError):
            load_snapshot(b"not a zip", "x.xlsx")
        with self.assertRaises(WorkbookError):
            load_snapshot(FIXTURE.read_bytes(), "x.xlsm")
        with self.assertRaises(WorkbookError):
            load_snapshot(b"0" * (5 * 1024 * 1024 + 1), "big.xlsx")

    def test_rejects_too_many_sheets(self):
        book = Workbook()
        for index in range(30):
            book.create_sheet(f"S{index}")
        buffer = io.BytesIO()
        book.save(buffer)
        with self.assertRaises(WorkbookError):
            load_snapshot(buffer.getvalue(), "many.xlsx")

    def test_range_limit(self):
        with self.assertRaises(WorkbookError):
            fixture().cells("Model", "A1:Z20", 200)
        with self.assertRaises(WorkbookError):
            fixture().cells("Nope", "A1", 200)


class ExportTests(unittest.TestCase):
    def test_error_like_input_is_literal_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = export_copy(fixture(), [change("B7", "#N/A")], directory, approved_at="now")
            book = load_workbook(path)
            self.assertEqual(book["Model"]["B7"].value, "#N/A")
            self.assertEqual(book["Model"]["B7"].data_type, "s")

    def test_export_applies_and_verifies(self):
        snapshot = fixture()
        before = hashlib.sha256(snapshot.data).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = export_copy(
                snapshot,
                [change("B7", 1661.5), change("B8", 220.5)],
                Path(directory),
                approved_at="2026-11-17T12:00:00Z",
            )
            self.assertTrue(path.name.endswith(".xlsx"))
            book = load_workbook(path)
            sheet = book["Model"]
            self.assertEqual(sheet["B7"].value, 1661.5)
            self.assertEqual(sheet["B8"].value, 220.5)
            self.assertEqual(sheet["B9"].value, "=B8/B7")
            self.assertIn("Cloudflare Q3 2024 release", sheet["B7"].comment.text)
            log = book["Provenance log"]
            self.assertEqual(log.max_row, 3)
            self.assertEqual(log["A2"].value, "Model!B7")
            self.assertTrue(book.calculation.fullCalcOnLoad)
        self.assertEqual(hashlib.sha256(snapshot.data).hexdigest(), before)

    def test_export_rejects_formula_change(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(WorkbookError, "New formulas"):
                export_copy(
                    fixture(),
                    [change("B8", "=B7*0.13")],
                    Path(directory),
                    approved_at="2026-11-17T12:00:00Z",
                )

    def test_export_names_do_not_collide(self):
        with tempfile.TemporaryDirectory() as directory:
            first = export_copy(fixture(), [change("B7", 1)], Path(directory), approved_at="t")
            second = export_copy(fixture(), [change("B7", 2)], Path(directory), approved_at="t")
            self.assertNotEqual(first, second)


def synthetic_book():
    book = Workbook()
    book.active.title = "Model"
    book.active["A1"] = 10
    book.active["B1"] = "=A1*2"
    return book


def book_bytes(book):
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def synthetic_snapshot(book=None):
    return load_snapshot(book_bytes(book or synthetic_book()), "synthetic.xlsx")


class IntegrityTests(unittest.TestCase):
    def test_saved_values_preserve_numeric_precision_and_time(self):
        book = synthetic_book()
        book.active["A1"] = 1.123456789012345
        book.active["C1"] = datetime.datetime(2026, 11, 20, 14, 25, 36)
        book.active["D1"] = datetime.time(14, 25, 36)
        snapshot = synthetic_snapshot(book)
        self.assertEqual(snapshot.cell("Model", 1, 1)["value"], "1.123456789012345")
        self.assertEqual(snapshot.cell("Model", 1, 1)["display"], "1.123456789")
        self.assertEqual(snapshot.cell("Model", 1, 3)["value"], "2026-11-20T14:25:36")
        self.assertEqual(snapshot.cell("Model", 1, 4)["value"], "14:25:36")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(WorkbookError, "old_value"):
                export_copy(
                    snapshot,
                    [{**change("A1", 2), "old_value": "1.123456789"}],
                    directory,
                    approved_at="t",
                )
            export_copy(
                snapshot,
                [{**change("A1", 2), "old_value": "1.123456789012345"}],
                directory,
                approved_at="t",
            )

    def test_export_without_optional_styles_part(self):
        buffer = io.BytesIO()
        with (
            zipfile.ZipFile(io.BytesIO(book_bytes(synthetic_book()))) as source,
            zipfile.ZipFile(buffer, "w") as target,
        ):
            for entry in source.infolist():
                if entry.filename == "xl/styles.xml":
                    continue
                data = source.read(entry.filename)
                if entry.filename in ("[Content_Types].xml", "xl/_rels/workbook.xml.rels"):
                    root = ET.fromstring(data)
                    for child in list(root):
                        if child.attrib.get("PartName") == "/xl/styles.xml" or child.attrib.get(
                            "Type", ""
                        ).endswith("/styles"):
                            root.remove(child)
                    data = ET.tostring(root)
                target.writestr(entry, data)
        snapshot = load_snapshot(buffer.getvalue(), "no-styles.xlsx")
        with tempfile.TemporaryDirectory() as directory:
            path = export_copy(snapshot, [change("A1", 20)], directory, approved_at="t")
            self.assertEqual(load_workbook(path)["Model"]["A1"].value, 20)

    def test_cell_metadata_and_missing_formula_cache(self):
        snapshot = synthetic_snapshot()
        value, formula, blank = snapshot.cells("Model", "A1:C1", 3)
        self.assertEqual(
            (value["kind"], value["value_status"], value["editable"]),
            ("value", "saved_value", True),
        )
        self.assertEqual(
            (blank["kind"], blank["value_status"], blank["editable"]),
            ("blank", "saved_value", True),
        )
        self.assertEqual(
            (formula["kind"], formula["value_status"], formula["editable"]),
            ("formula", "missing_formula_cache", False),
        )
        self.assertIn("Formula", formula["edit_block_reason"])
        self.assertEqual(
            snapshot.info()["export_calculation_status"], "pending_excel_recalculation"
        )
        # A saved cache is still historical, including a legitimate zero result.
        buffer = io.BytesIO()
        with (
            zipfile.ZipFile(io.BytesIO(snapshot.data)) as source,
            zipfile.ZipFile(buffer, "w") as target,
        ):
            for entry in source.infolist():
                data = source.read(entry.filename)
                if entry.filename == "xl/worksheets/sheet1.xml":
                    data = re.sub(rb"(<f>A1\*2</f>)<v\s*/>", rb"\1<v>0</v>", data)
                target.writestr(entry, data)
        cached = load_snapshot(buffer.getvalue(), "cached.xlsx").cell("Model", 1, 2)
        self.assertEqual((cached["value_status"], cached["value"]), ("cached_formula", "0"))

    def test_unsafe_targets_blocked_at_validation_and_export(self):
        book = synthetic_book()
        book.active.merge_cells("C2:D3")
        book.active.append(["Header", "Other"])
        book.active.add_table(Table(displayName="Inputs", ref="F1:G2"))
        book.active["F1"], book.active["G1"] = "First", "Second"
        book.active["H1"] = ArrayFormula(ref="H1:I2", text="=A1:A2*2")
        hidden = book.create_sheet("Hidden")
        hidden.sheet_state = "hidden"
        protected = book.create_sheet("Protected")
        protected.protection.sheet = True
        snapshot = synthetic_snapshot(book)
        for sheet, address in [
            ("Model", "B1"),
            ("Model", "C2"),
            ("Model", "D3"),
            ("Model", "G2"),
            ("Model", "I2"),
            ("Hidden", "A1"),
            ("Protected", "A1"),
        ]:
            with self.subTest(sheet=sheet, address=address):
                with self.assertRaises(WorkbookError):
                    snapshot.validate_edit_target(sheet, address)
                with tempfile.TemporaryDirectory() as directory:
                    edit = {**change(address, 20), "sheet": sheet}
                    with self.assertRaises(WorkbookError):
                        export_copy(snapshot, [edit], directory, approved_at="t")
                    self.assertEqual(list(Path(directory).iterdir()), [])

    def test_duplicates_and_stale_preconditions_rejected(self):
        snapshot = synthetic_snapshot()
        cases = [
            [change("A1", 20), change("$a$1", 30)],
            [{**change("A1", 20), "old_display": "11"}],
            [{**change("A1", 20), "old_formula": "=1"}],
            [{**change("A1", 20), "old_value": "11"}],
        ]
        for edits in cases:
            with self.subTest(edits=edits), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(WorkbookError):
                    export_copy(snapshot, edits, directory, approved_at="t")
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_comments_formulas_styles_and_audit_text_preserved(self):
        book = synthetic_book()
        book.active["A1"].comment = Comment("Existing analyst assumption", "Analyst")
        book.active["B1"].comment = Comment("Keep this", "Reviewer")
        book.active["B1"].font = Font(bold=True)
        book.active["B1"].number_format = "0.00"
        book.active["C1"] = "Unchanged"
        book.active["C1"].hyperlink = "https://example.com/"
        book.create_sheet("provenance LOG")["A1"] = "User-owned history"
        snapshot = synthetic_snapshot(book)
        edit = {
            **change("A1", 20),
            "rationale": '=HYPERLINK("https://example.com")',
            "old_display": "10",
            "old_formula": None,
            "old_value": "10",
        }
        with tempfile.TemporaryDirectory() as directory:
            result = load_workbook(export_copy(snapshot, [edit], directory, approved_at="=1+1"))
            self.assertEqual(result["Model"]["A1"].value, 20)
            self.assertEqual(result["Model"]["B1"].value, "=A1*2")
            self.assertTrue(result["Model"]["B1"].font.bold)
            self.assertEqual(result["Model"]["B1"].comment.text, "Keep this")
            self.assertIn("Existing analyst assumption", result["Model"]["A1"].comment.text)
            self.assertEqual(result["Model"]["A1"].comment.author, "Analyst")
            self.assertEqual(result["provenance LOG"]["A1"].value, "User-owned history")
            self.assertEqual(result["Provenance log 2"]["E2"].data_type, "s")
            self.assertEqual(result["Provenance log 2"]["I2"].data_type, "s")
            self.assertEqual(result.calculation.calcMode, "auto")
            self.assertTrue(result.calculation.forceFullCalc)

    def test_fidelity_risks_block_export_but_allow_reads(self):
        book = synthetic_book()
        book.active.add_chart(BarChart(), "D1")
        snapshot = synthetic_snapshot(book)
        self.assertIn("charts", snapshot.info()["export_blockers"])
        self.assertEqual(snapshot.cell("Model", 1, 1)["value"], "10")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(WorkbookError, "export is blocked"):
                export_copy(snapshot, [change("A1", 20)], directory, approved_at="t")

    def test_archive_feature_detection_and_expansion_guard(self):
        from provenance.web.workbook import _inspect_archive

        base = book_bytes(synthetic_book())
        for name, expected in [
            ("xl/media/image1.png", "images or drawings"),
            ("xl/pivotTables/pivot1.xml", "pivot tables"),
            ("xl/chartsheets/sheet1.xml", "charts"),
            ("xl/externalLinks/link1.xml", "external workbook links"),
            ("customXml/item1.xml", "unsupported workbook metadata"),
        ]:
            buffer = io.BytesIO(base)
            with zipfile.ZipFile(buffer, "a") as archive:
                archive.writestr(name, "<root/>")
            self.assertIn(expected, _inspect_archive(buffer.getvalue()))
        buffer = io.BytesIO(base)
        with zipfile.ZipFile(buffer, "a", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("oversized.xml", b"0" * 10000)
        with (
            patch("provenance.web.workbook.MAX_INFLATED_BYTES", 10000),
            patch("provenance.web.workbook.load_workbook") as loader,
        ):
            with self.assertRaisesRegex(WorkbookError, "expanded"):
                load_snapshot(buffer.getvalue(), "bomb.xlsx")
            loader.assert_not_called()

    def test_default_extensions_preserved_and_other_extensions_blocked(self):
        namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        extension = (
            '<extLst><ext uri="test"><calcFeatures '
            'xmlns="http://schemas.microsoft.com/office/spreadsheetml/2018/calcfeatures">'
            '<feature name="microsoft.com:RD"/></calcFeatures></ext></extLst>'
        )
        original = book_bytes(synthetic_book())
        for supported in (True, False):
            buffer = io.BytesIO()
            with (
                zipfile.ZipFile(io.BytesIO(original)) as source,
                zipfile.ZipFile(buffer, "w") as target,
            ):
                for entry in source.infolist():
                    data = source.read(entry.filename)
                    if entry.filename == "xl/workbook.xml":
                        extra = (
                            extension
                            if supported
                            else extension.replace("calcFeatures", "unknownFeature")
                        )
                        data = data.replace(b"</workbook>", extra.encode() + b"</workbook>")
                    target.writestr(entry, data)
            snapshot = load_snapshot(buffer.getvalue(), "extension.xlsx")
            if not supported:
                self.assertIn("unsupported XML extensions", snapshot.export_blockers)
                continue
            self.assertEqual(snapshot.export_blockers, [])
            with tempfile.TemporaryDirectory() as directory:
                path = export_copy(snapshot, [change("A1", 20)], directory, approved_at="t")
                with (
                    zipfile.ZipFile(path) as result,
                    zipfile.ZipFile(io.BytesIO(snapshot.data)) as source,
                ):
                    before = ET.fromstring(source.read("xl/workbook.xml")).find(
                        f"{{{namespace}}}extLst"
                    )
                    after = ET.fromstring(result.read("xl/workbook.xml")).find(
                        f"{{{namespace}}}extLst"
                    )
                    self.assertEqual(ET.tostring(before), ET.tostring(after))

    def test_disguised_macros_and_xml_entities_rejected_before_parsing(self):
        from provenance.web.workbook import _inspect_archive

        for name, data in [
            ("xl/vbaProject.bin", b"binary"),
            ("extra.xml", b'<!DOCTYPE x [<!ENTITY a "bad">]><x>&a;</x>'),
        ]:
            buffer = io.BytesIO(book_bytes(synthetic_book()))
            with zipfile.ZipFile(buffer, "a") as archive:
                archive.writestr(name, data)
            with self.assertRaises(WorkbookError):
                _inspect_archive(buffer.getvalue())

    def test_failed_preservation_verification_removes_download(self):
        snapshot = synthetic_snapshot()
        from openpyxl.workbook.workbook import Workbook as WorkbookType

        original_save = WorkbookType.save

        def corrupt(book, filename):
            book["Model"]["B1"] = "=99"
            original_save(book, filename)

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(WorkbookType, "save", corrupt),
        ):
            with self.assertRaisesRegex(WorkbookError, "non-target content changed"):
                export_copy(snapshot, [change("A1", 20)], directory, approved_at="t")
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
