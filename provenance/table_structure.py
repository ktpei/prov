"""Extract deterministic native HTML table geometry without interpreting values.

Limits are intentionally conservative: spans may not exceed 1,000 and a table may
not address more than 10,000 logical columns. Nested tables are separate tables.
"""

import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

MAX_SPAN = 1_000
MAX_COLUMNS = 10_000
SUPPRESSED_TAGS = {"head", "script", "style", "noscript", "ix:header"}
LIMITATIONS = [
    "Cell text is decoded, whitespace-normalized extracted content, not an original HTML byte quote.",
    "Nested tables are extracted independently and their text and cells are excluded from parent cells.",
    "Tables may be layout or decorative; extraction does not establish header associations or entailment.",
    "No value, sign, unit, period, header, metric identity, or financial meaning is inferred.",
    f"Row and column spans are limited to {MAX_SPAN}; logical columns are limited to {MAX_COLUMNS}.",
    "Only unambiguous optional td, th, and tr end tags are handled; unfinished structures are rejected.",
]


def _location(position):
    return {"line": position[0], "column": position[1]}


def _positive_span(attrs, name):
    values = [value for key, value in attrs if key == name]
    if len(values) > 1:
        raise ValueError(f"Duplicate {name}")
    raw = values[0] if values else "1"
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}: {raw!r}") from exc
    if not 1 <= value <= MAX_SPAN:
        raise ValueError(f"Invalid {name}: {raw!r}")
    return value


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.stack = []
        self.suppressed = []

    def _current(self):
        return self.stack[-1] if self.stack else None

    def _close_cell(self, table):
        cell = table["cell"]
        if cell is None:
            return
        cell["record"]["text"] = " ".join("".join(cell["parts"]).split())
        table["cell"] = None

    def _close_row(self, table):
        if table["row"] is None:
            return
        self._close_cell(table)
        table["row"] = None

    def _start_row(self, table):
        self._close_row(table)
        index = len(table["record"]["rows"])
        row = {"index": index, "cells": []}
        table["record"]["rows"].append(row)
        table["row"] = row

    def _start_cell(self, table, tag, attrs):
        if table["row"] is None:
            raise ValueError("Cell outside an active row")
        self._close_cell(table)
        row_index = table["row"]["index"]
        row_span = _positive_span(attrs, "rowspan")
        column_span = _positive_span(attrs, "colspan")
        column = 0
        while table["occupied"].get(column, 0) > row_index:
            column += 1
        if column + column_span > MAX_COLUMNS:
            raise ValueError(f"Table exceeds {MAX_COLUMNS} logical columns")
        if any(
            table["occupied"].get(col, 0) > row_index for col in range(column, column + column_span)
        ):
            raise ValueError("Cell span overlaps an occupied rowspan")
        attributes = dict(attrs)
        record = {
            "id": f"{table['record']['id']}-r{row_index}-c{column}",
            "row_start": row_index,
            "column_start": column,
            "row_span": row_span,
            "column_span": column_span,
            "tag": tag,
            "text": "",
            "original_location": _location(self.getpos()),
        }
        if "id" in attributes:
            record["html_id"] = attributes["id"]
        table["row"]["cells"].append(record)
        for col in range(column, column + column_span):
            table["occupied"][col] = row_index + row_span
        table["cell"] = {"record": record, "parts": []}

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.suppressed:
            if tag in SUPPRESSED_TAGS:
                self.suppressed.append(tag)
            return
        if tag in SUPPRESSED_TAGS:
            self.suppressed.append(tag)
            return
        if tag == "table":
            number = len(self.tables) + 1
            record = {
                "id": f"table-{number}",
                "original_location": _location(self.getpos()),
                "rows": [],
            }
            attributes = dict(attrs)
            if "id" in attributes:
                record["html_id"] = attributes["id"]
            self.tables.append(record)
            self.stack.append({"record": record, "row": None, "cell": None, "occupied": {}})
            return
        table = self._current()
        if table is None:
            return
        if tag == "tr":
            self._start_row(table)
        elif tag in {"td", "th"}:
            self._start_cell(table, tag, attrs)
        elif tag == "br" and table["cell"] is not None:
            table["cell"]["parts"].append(" ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.suppressed:
            if tag == self.suppressed[-1]:
                self.suppressed.pop()
            return
        table = self._current()
        if table is None:
            return
        if tag in {"td", "th"}:
            self._close_cell(table)
        elif tag == "tr":
            self._close_row(table)
        elif tag == "table":
            self._close_row(table)
            self.stack.pop()

    def handle_data(self, data):
        if self.suppressed or not self.stack:
            return
        table = self._current()
        if table["cell"] is not None:
            table["cell"]["parts"].append(data)

    def finish(self):
        if self.suppressed:
            raise ValueError(f"Unfinished suppressed element: {self.suppressed[-1]}")
        if self.stack:
            table = self._current()
            active = "cell" if table["cell"] is not None else "row" if table["row"] else "table"
            raise ValueError(f"Unfinished active {active}")


def extract_html_tables(path):
    """Return a versioned JSON-compatible table sidecar for *path*."""
    raw = Path(path).read_bytes()
    parser = _TableParser()
    parser.feed(raw.decode("utf-8", errors="strict"))
    parser.close()
    parser.finish()
    return {
        "version": "native-html-tables-v1",
        "original_sha256": hashlib.sha256(raw).hexdigest(),
        "tables": parser.tables,
        "limitations": LIMITATIONS.copy(),
    }


def main():
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("input_html", type=Path)
    argument_parser.add_argument("output_json", type=Path)
    args = argument_parser.parse_args()
    sidecar = extract_html_tables(args.input_html)
    encoded = (json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n").encode()
    with args.output_json.open("xb") as output:
        output.write(encoded)
    rows = sum(len(table["rows"]) for table in sidecar["tables"])
    cells = sum(len(row["cells"]) for table in sidecar["tables"] for row in table["rows"])
    print(
        json.dumps(
            {
                "tables": len(sidecar["tables"]),
                "rows": rows,
                "cells": cells,
                "original_sha256": sidecar["original_sha256"],
                "sidecar_sha256": hashlib.sha256(encoded).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
