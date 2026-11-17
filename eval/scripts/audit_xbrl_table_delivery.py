"""Measure existing table-read delivery with oracle fact-to-row locations, not search."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from provenance.table_tools import TableSources

ROOT = Path(__file__).resolve().parents[2]
FACTS = ROOT / "eval/reports/xbrl-facts-2026-11-16/facts.json"
CORPUS = ROOT / "runs/native-html-v1-issuer-eligibility/old-dominion-2025-06-30-10q"
SOURCE = "old-dominion-2025-06-30-10q"
TABLES = ROOT / "runs/native-html-v1-issuer-eligibility/old-dominion-2025-06-30-10q-tables.json"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build():
    paths = [FACTS, TABLES, CORPUS / "sources.json", Path(__file__).resolve()]
    paths.extend(
        ROOT / "provenance" / name
        for name in ("table_tools.py", "table_structure.py", "sources.py", "html_text.py")
    )
    captured = {path: path.read_bytes() for path in paths}
    if sha(captured[FACTS]) != "11462530f838361ad867201079ea6252f9c02703f9d4e20ec37a080220ee7986":
        raise ValueError("Frozen typed export differs")
    facts = json.loads(captured[FACTS])
    manifest = json.loads(captured[CORPUS / "sources.json"])
    source = next(item for item in manifest["sources"] if item["id"] == SOURCE)
    original = CORPUS / source["original_file"]
    captured[original] = original.read_bytes()
    if sha(captured[original]) != facts["original_sha256"]:
        raise ValueError("Original source differs")
    tables = TableSources(CORPUS)
    snapshot = tables._sources[SOURCE]
    if sha(captured[TABLES]) != facts["input_sha256"][str(TABLES.relative_to(ROOT))] or snapshot[
        "sidecar"
    ] != json.loads(captured[TABLES]):
        raise ValueError("Regenerated table geometry differs from bound sidecar")
    cells = {
        (table["id"], cell["id"]): (row["index"], cell)
        for table in snapshot["sidecar"]["tables"]
        for row in table["rows"]
        for cell in row["cells"]
    }
    traces, cases = {}, []
    for fact in facts["facts"]:
        occurrence = fact["source_occurrence"]
        mapping = occurrence["table_mapping"]
        case = {
            "fact_id": fact["id"],
            "value_kind": fact["value"]["kind"],
            "source_disposition": occurrence["source_disposition"],
            "table_mapping": mapping,
        }
        if mapping is None:
            case["delivery"] = "no_mapped_cell"
        else:
            row, cell = cells[(mapping["table_id"], mapping["cell_id"])]
            key = f"{mapping['table_id']}:row:{row}"
            if key not in traces:
                args = {"source_id": SOURCE, "table_id": mapping["table_id"], "row_indices": [row]}
                response = tables.call("read_table", args, timeout=10)
                serialized = json.dumps(
                    response,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                traces[key] = {
                    "tool": "read_table",
                    "args": args,
                    "response": response,
                    "response_sha256": sha(serialized.encode()),
                    "response_characters": len(serialized),
                }
            response = traces[key]["response"]
            returned = {item["id"] for item in response.get("cells", [])}
            case.update(
                trace_id=key,
                source_cell_empty=not bool(cell["text"]),
                source_cell_visibility=cell["visibility"],
                delivery="read_error"
                if "error" in response
                else "cell_returned"
                if mapping["cell_id"] in returned
                else "cell_omitted",
            )
        cases.append(case)
    if len(cases) != 504 or len({case["fact_id"] for case in cases}) != 504:
        raise ValueError("Fact denominator differs")
    if any(path.read_bytes() != raw for path, raw in captured.items()):
        raise ValueError("Audit inputs changed")
    return {
        "version": "xbrl-oracle-table-delivery-audit-v1",
        "method": "Oracle nearest-cell row; one existing table-window read per unique table/row; no search or model calls.",
        "limitations": [
            "Returned cell identity does not prove fact value, context, unit or financial answer delivery.",
            "No-mapped-cell includes hidden and outside-table facts; this is not a search failure.",
            "This exposed-source diagnostic is not prospective benchmark accuracy.",
        ],
        "source_availability": source["availability"],
        "artifact_class": source["artifact_class"],
        "original_sha256": facts["original_sha256"],
        "input_sha256": {str(path.relative_to(ROOT)): sha(raw) for path, raw in captured.items()},
        "summary": {
            "facts": len(cases),
            "unique_reads": len(traces),
            "delivery": dict(sorted(Counter(case["delivery"] for case in cases).items())),
            "by_value_kind": {
                kind: dict(
                    sorted(
                        Counter(
                            case["delivery"] for case in cases if case["value_kind"] == kind
                        ).items()
                    )
                )
                for kind in sorted({case["value_kind"] for case in cases})
            },
        },
        "cases": cases,
        "traces": traces,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["summary"], indent=2))
