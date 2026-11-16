"""Extract deterministic native HTML table geometry without interpreting values.

Limits are intentionally conservative: spans may not exceed 1,000 and a table may
not address more than 10,000 logical columns. Nested tables are separate tables.
"""

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

MAX_SPAN = 1_000
MAX_COLUMNS = 10_000
SUPPRESSED_TAGS = {"head", "script", "style", "noscript", "ix:header"}
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
BLOCK_TAGS = {
    "p",
    "div",
    "li",
    "section",
    "article",
    "header",
    "footer",
    "main",
    "nav",
    "aside",
    "blockquote",
    "pre",
    "address",
    "dl",
    "dt",
    "dd",
    "ul",
    "ol",
    "figure",
    "figcaption",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "fieldset",
    "legend",
    "summary",
    "details",
}
LIMITATIONS = [
    "Cell text is decoded, whitespace-normalized extracted content, not an original HTML byte quote.",
    "Nested tables are extracted independently and their text and cells are excluded from parent cells.",
    "Tables may be layout or decorative; extraction does not establish header associations or entailment.",
    "No value, sign, unit, period, header, metric identity, or financial meaning is inferred.",
    "Only explicit HTML hidden attributes and simple inline display or visibility styles are recorded; external CSS visibility is unresolved.",
    "HTML scope, headers, and id attributes are recorded without resolving header associations.",
    f"Row and column spans are limited to {MAX_SPAN}; logical columns are limited to {MAX_COLUMNS}.",
    "HTML rowspan=0 is valid HTML but intentionally unsupported and rejected.",
    "Hidden cell self-closing slashes are ignored until an explicit or implicit cell end; other hidden non-void self-closing elements are rejected.",
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
    if name == "rowspan" and value == 0:
        raise ValueError("Unsupported rowspan=0")
    if not 1 <= value <= MAX_SPAN:
        raise ValueError(f"Invalid {name}: {raw!r}")
    return value


def _is_explicitly_hidden(attrs):
    """Recognize only hiding that is explicit in the element's HTML."""
    for key, value in attrs:
        if key.lower() == "hidden":
            return True
        if key.lower() != "style" or value is None:
            continue
        for declaration in value.split(";"):
            if ":" not in declaration:
                continue
            property_name, property_value = declaration.split(":", 1)
            property_name = "".join(property_name.lower().split())
            property_value = " ".join(property_value.lower().split())
            property_value = re.sub(r"!\s*important$", "", property_value).rstrip()
            if property_name == "display" and property_value == "none":
                return True
            if property_name == "visibility" and property_value in {"hidden", "collapse"}:
                return True
    return False


class _TableParser(HTMLParser):
    def __init__(self, *, version="native-html-tables-v2"):
        super().__init__(convert_charrefs=True)
        self.version = version
        self.template_depth = 0
        self.tables = []
        self.stack = []
        self.blocked = []

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

    def _start_cell(self, table, tag, attrs, explicitly_hidden):
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
            "visibility": "explicitly_hidden" if explicitly_hidden else "not_explicitly_hidden",
            "original_location": _location(self.getpos()),
        }
        if "id" in attributes:
            record["html_id"] = attributes["id"]
        if "scope" in attributes:
            record["scope"] = attributes["scope"]
        if "headers" in attributes:
            record["headers"] = (attributes["headers"] or "").split()
        table["row"]["cells"].append(record)
        for col in range(column, column + column_span):
            table["occupied"][col] = row_index + row_span
        table["cell"] = {"record": record, "parts": []}

    def _start_block(self, tag, cell=False, row=False, table=False, self_closing=False):
        if not self_closing and tag not in VOID_TAGS:
            self.blocked.append({"tag": tag, "cell": cell, "row": row, "table": table})

    def _starttag(self, tag, attrs, self_closing=False):
        tag = tag.lower()
        if self.version == "native-html-tables-v3":
            if (self.template_depth or not self.blocked) and tag in {
                "textarea",
                "title",
                "xmp",
                "iframe",
                "noembed",
                "noframes",
                "noscript",
                "plaintext",
            }:
                # HTMLParser only implements raw-text tokenization for script/style.
                # Literal </template> text elsewhere must not escape the inert subtree.
                raise ValueError("Unsupported raw-text context for template-aware extraction")
            if tag == "template":
                if self_closing:
                    raise ValueError("Unsupported self-closing template")
                if any(name == "shadowrootmode" for name, _ in attrs):
                    raise ValueError("Unsupported declarative shadow DOM template")
                self.template_depth += 1
                return
            if self.template_depth:
                return
        if self.blocked and self.blocked[-1]["cell"] and tag in {"td", "th", "tr"}:
            self._close_cell(self._current())
            self.blocked.pop()  # An incoming cell/row implicitly ends the preceding cell.
        is_hidden = _is_explicitly_hidden(attrs)
        is_blocked = bool(self.blocked)
        is_blocked_table = any(block["table"] for block in self.blocked)
        if tag in SUPPRESSED_TAGS:
            self._start_block(tag, self_closing=self_closing)
            return
        if tag == "table" and not (is_blocked or is_hidden):
            parent = self._current()
            if parent is not None:
                target = parent.get("caption") or parent["cell"]
                if target is not None:
                    target["parts"].append(" ")
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
            self.stack.append(
                {"record": record, "row": None, "cell": None, "occupied": {}, "caption": None}
            )
            return
        table = self._current()
        if tag == "table":
            self._start_block(tag, table=True, self_closing=self_closing)
            return
        if table is None:
            if is_blocked or is_hidden:
                self._start_block(tag, self_closing=self_closing)
            return
        if is_blocked_table:
            self._start_block(tag, self_closing=self_closing)
            return
        if tag == "tr":
            self._start_row(table)
            if is_blocked or is_hidden:
                self._start_block(tag, row=True, self_closing=self_closing)
            elif self_closing:
                self._close_row(table)
        elif tag in {"td", "th"}:
            self._start_cell(table, tag, attrs, explicitly_hidden=is_blocked or is_hidden)
            if is_blocked or is_hidden:
                self._start_block(tag, cell=True, self_closing=self_closing)
            elif self_closing:
                self._close_cell(table)
        elif tag == "caption" and not (is_blocked or is_hidden):
            table["caption"] = {"parts": [], "original_location": _location(self.getpos())}
        elif (tag == "br" or tag in BLOCK_TAGS) and not (is_blocked or is_hidden):
            target = table.get("caption") or table["cell"]
            if target is not None:
                target["parts"].append(" ")
        elif is_blocked or is_hidden:
            self._start_block(tag, self_closing=self_closing)

    def handle_starttag(self, tag, attrs):
        self._starttag(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        if self.version == "native-html-tables-v3" and (
            self.template_depth or tag.lower() == "template"
        ):
            self._starttag(tag, attrs, self_closing=True)
            return
        if tag.lower() in {"td", "th"} and _is_explicitly_hidden(attrs):
            self._starttag(tag, attrs)  # HTML ignores the slash on non-void cells.
            return
        if tag.lower() not in VOID_TAGS and (
            _is_explicitly_hidden(attrs)
            or tag.lower() in SUPPRESSED_TAGS
            or (self.blocked and ":" not in tag and tag.lower() not in {"td", "th"})
        ):
            raise ValueError("Unsupported self-closing non-void HTML element with hidden content")
        self._starttag(tag, attrs, self_closing=True)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.version == "native-html-tables-v3":
            if tag == "template":
                if not self.template_depth:
                    raise ValueError("Unmatched template end tag")
                self.template_depth -= 1
                return
            if self.template_depth:
                return
        if self.blocked and self.blocked[-1]["cell"] and tag in {"tr", "table"}:
            self._close_cell(self._current())
            self.blocked.pop()
        if self.blocked:
            block = self.blocked[-1]
            if tag != block["tag"]:
                raise ValueError(
                    f"Ambiguous malformed hidden structure: expected </{block['tag']}>"
                )
            if block["cell"]:
                self._close_cell(self._current())
            if block["row"]:
                self._close_row(self._current())
            self.blocked.pop()
            return
        table = self._current()
        if table is None:
            return
        if tag in {"td", "th"}:
            self._close_cell(table)
        elif tag == "tr":
            self._close_row(table)
        elif tag == "caption" and table.get("caption") is not None:
            caption = table.pop("caption")
            table["record"]["caption"] = {
                "text": " ".join("".join(caption["parts"]).split()),
                "original_location": caption["original_location"],
            }
        elif tag == "table":
            self._close_row(table)
            self.stack.pop()
            parent = self._current()
            if parent is not None:
                target = parent.get("caption") or parent["cell"]
                if target is not None:
                    target["parts"].append(" ")
        elif tag in BLOCK_TAGS:
            target = table.get("caption") or table["cell"]
            if target is not None:
                target["parts"].append(" ")

    def handle_data(self, data):
        if self.template_depth or self.blocked or not self.stack:
            return
        table = self._current()
        if table.get("caption") is not None:
            table["caption"]["parts"].append(data)
        elif (
            table["cell"] is not None
            and table["cell"]["record"]["visibility"] != "explicitly_hidden"
        ):
            table["cell"]["parts"].append(data)

    def finish(self):
        if self.template_depth:
            raise ValueError("Unfinished template")
        if self.blocked:
            raise ValueError(f"Unfinished hidden or suppressed element: {self.blocked[-1]['tag']}")
        if self.stack:
            table = self._current()
            active = "cell" if table["cell"] is not None else "row" if table["row"] else "table"
            raise ValueError(f"Unfinished active {active}")


def extract_html_tables(path, *, version="native-html-tables-v2"):
    """Return a versioned JSON-compatible table sidecar for *path*."""
    if version not in {"native-html-tables-v2", "native-html-tables-v3"}:
        raise ValueError("Unknown table extraction version")
    raw = Path(path).read_bytes()
    parser = _TableParser(version=version)
    parser.feed(raw.decode("utf-8", errors="strict"))
    parser.close()
    parser.finish()
    return {
        "version": version,
        "original_sha256": hashlib.sha256(raw).hexdigest(),
        "tables": parser.tables,
        "limitations": LIMITATIONS.copy()
        + (
            [
                "Ordinary template contents are excluded; declarative shadow DOM templates are unsupported and rejected.",
                "RCDATA and raw-text elements are rejected outside already-suppressed content and inside templates, except script/style whose tokenization is supported.",
            ]
            if version == "native-html-tables-v3"
            else []
        ),
    }


def main():
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("input_html", type=Path)
    argument_parser.add_argument("output_json", type=Path)
    argument_parser.add_argument(
        "--version",
        choices=["native-html-tables-v2", "native-html-tables-v3"],
        default="native-html-tables-v2",
    )
    args = argument_parser.parse_args()
    sidecar = extract_html_tables(args.input_html, version=args.version)
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
