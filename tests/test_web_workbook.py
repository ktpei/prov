import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook

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
        self.assertEqual([cell["value"] for cell in cells], ["1650", "215", "0.1303030303"])
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

    def test_export_formula_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = export_copy(
                fixture(),
                [change("B8", "=B7*0.13")],
                Path(directory),
                approved_at="2026-11-17T12:00:00Z",
            )
            self.assertEqual(load_workbook(path)["Model"]["B8"].value, "=B7*0.13")

    def test_export_names_do_not_collide(self):
        with tempfile.TemporaryDirectory() as directory:
            first = export_copy(fixture(), [change("B7", 1)], Path(directory), approved_at="t")
            second = export_copy(fixture(), [change("B7", 2)], Path(directory), approved_at="t")
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
