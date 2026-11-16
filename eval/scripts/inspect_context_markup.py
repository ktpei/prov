"""Descriptive context-markup inventory of four already-exposed HTML snapshots."""

import argparse
import hashlib
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from provenance.table_structure import extract_html_tables

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "eval/reports/table-template-2026-11-16/compatibility.json"


class TagInventory(HTMLParser):
    """Count lexical colon-tag names, not namespace-resolved or validated facts."""

    def __init__(self):
        super().__init__()
        self.tags = Counter()

    def handle_starttag(self, tag, attrs):
        if ":" in tag:
            self.tags[tag] += 1


def inventory():
    paths = [BASELINE, Path(__file__), ROOT / "provenance/table_structure.py"]
    captured = {p: p.read_bytes() for p in paths}
    entries = json.loads(captured[BASELINE])["documents"]
    rows = []
    for entry in entries:
        path = ROOT / entry["path"]
        raw = path.read_bytes()
        captured[path] = raw
        if hashlib.sha256(raw).hexdigest() != entry["original_sha256"]:
            raise ValueError("Historical source identity differs")
        parser = TagInventory()
        parser.feed(raw.decode("utf-8", errors="strict"))
        parser.close()
        row = {
            "path": entry["path"],
            "original_sha256": entry["original_sha256"],
            "lexical_colon_tag_counts": dict(sorted(parser.tags.items())),
            "tables": {},
        }
        for version in ("native-html-tables-v2", "native-html-tables-v3"):
            try:
                sidecar = extract_html_tables(path, version=version)
            except ValueError as error:
                row["tables"][version] = {"status": "rejected", "error": str(error)}
                continue
            if sidecar["original_sha256"] != entry["original_sha256"]:
                raise ValueError("Extractor used different source bytes")
            cells = [c for t in sidecar["tables"] for r in t["rows"] for c in r["cells"]]
            row["tables"][version] = {
                "status": "extracted",
                "table_count": len(sidecar["tables"]),
                "cell_count": len(cells),
                "th_count": sum(c["tag"] == "th" for c in cells),
                "headers_attribute_count": sum("headers" in c for c in cells),
                "scope_counts": dict(Counter(c["scope"] for c in cells if "scope" in c)),
            }
        rows.append(row)
    if any(path.read_bytes() != raw for path, raw in captured.items()):
        raise ValueError("Context-markup inventory input changed")
    return {
        "version": "exposed-context-markup-inventory-v1",
        "input_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(b).hexdigest() for p, b in captured.items()
        },
        "documents": rows,
        "limitations": [
            "Descriptive development inspection, not a prospective benchmark or representative sample.",
            "Colon-tag counts are lexical HTMLParser observations, not resolved namespaces, usable facts, visibility or XBRL validation.",
            "Header counts describe extracted table cells only; absent markup does not mean absent visual headers.",
            "All four source dispositions are retained; extraction rejection is not financial inaccuracy.",
            "No new source acquisition, ranking, provider call or validation-content access.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = inventory()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
