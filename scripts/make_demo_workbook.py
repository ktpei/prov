"""Build the public-data demo workbook used by the web MVP.

Usage: uv run python scripts/make_demo_workbook.py data/demo/cloudflare-fy2024-model.xlsx

The committed fixture is this output after one open/save in Microsoft Excel, so
formula cells carry cached values and the snapshot hash stays stable.
"""

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

ROWS = [
    ("Q3 2024 revenue (analyst estimate)", 425.0, "USD million", "Analyst estimate"),
    ("Q4 2024 revenue (analyst assumption)", 445.0, "USD million", "Analyst assumption"),
    ("FY2024 revenue (analyst assumption)", 1650.0, "USD million", "Analyst assumption"),
    (
        "FY2024 non-GAAP operating income (analyst assumption)",
        215.0,
        "USD million",
        "Analyst assumption",
    ),
    ("Implied FY2024 non-GAAP operating margin", "=B8/B7", "%", "Formula"),
]


def build(path):
    book = Workbook()
    sheet = book.active
    sheet.title = "Model"
    sheet["A1"] = "Cloudflare, Inc. (NET) — FY2024 operating model (demo)"
    sheet["A1"].font = Font(bold=True, size=13)
    sheet["A2"] = (
        "Demo workbook. Inputs below are analyst assumptions dated 2024-08-15, before Q3 results."
    )
    for column, header in zip("ABCD", ("Metric", "Value", "Unit", "Note"), strict=True):
        sheet[f"{column}4"] = header
        sheet[f"{column}4"].font = Font(bold=True)
    for offset, row in enumerate(ROWS):
        for column, value in zip("ABCD", row, strict=True):
            sheet[f"{column}{5 + offset}"] = value
    sheet["B9"].number_format = "0.0%"
    for cell in ("B5", "B6", "B7", "B8"):
        sheet[cell].number_format = "#,##0.0"
    sheet.column_dimensions["A"].width = 52
    sheet.column_dimensions["B"].width = 12
    sheet.column_dimensions["C"].width = 14
    sheet.column_dimensions["D"].width = 20
    notes = book.create_sheet("Notes")
    notes["A1"] = (
        "Public-data demo for the Provenance web MVP. Values in Model!B5:B8 are fictional "
        "analyst assumptions to be checked against Cloudflare's Q3 2024 release."
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    book.save(path)


if __name__ == "__main__":
    build(Path(sys.argv[1]))
