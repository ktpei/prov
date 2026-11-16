"""Run the fixed, offline table-tool protocol; no model calls or answer injection.

Run from repository root: uv run python -m eval.scripts.table_runtime_probe
with --protocol, --fixtures, --corpus, and a new --output directory.
"""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from provenance.sources import Sources
from provenance.table_evaluation import grade_table_read
from provenance.table_structure import extract_html_tables
from provenance.table_tools import TableSources


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )


def run(protocol_path, fixture_path, corpus, output):
    protocol_raw, fixture_raw = protocol_path.read_bytes(), fixture_path.read_bytes()
    protocol, fixtures = json.loads(protocol_raw), json.loads(fixture_raw)
    if protocol["version"] != "table-runtime-development-protocol-v1":
        raise ValueError("Unsupported protocol")
    if protocol["fixture_file_sha256"] != digest(fixture_raw):
        raise ValueError("Frozen fixture identity mismatch")
    by_id = {fixture["id"]: fixture for fixture in fixtures["fixtures"]}
    cases = protocol["cases"]
    if (
        not cases
        or len(by_id) != len(fixtures["fixtures"])
        or len({case["id"] for case in cases}) != len(cases)
        or any(case["id"] not in by_id for case in cases)
    ):
        raise ValueError("Unique known fixture cases required")
    if protocol["response_limit_characters"] != 12000:
        raise ValueError("Protocol must match fixed runtime response cap")
    output.mkdir(parents=True, exist_ok=False)
    sources = Sources(corpus)
    source = sources.documents[protocol["source_id"]]
    if source["original_sha256"] != protocol["original_sha256"]:
        raise ValueError("Protocol original hash mismatch")
    sidecar = extract_html_tables(corpus / source["original_file"])
    tables = TableSources(corpus)
    report = {
        "version": "table-runtime-probe-v1",
        "protocol_sha256": digest(protocol_raw),
        "fixture_file_sha256": digest(fixture_raw),
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True)
        ),
        "model_calls": 0,
        "conditions": {},
        "limitations": protocol["limitations"],
    }
    for condition in ("window_oracle", "question_search_top1"):
        rows = []
        for case in cases:
            fixture = by_id[case["id"]]
            trace = []

            def call(name, args, trace=trace):
                started = time.monotonic()
                response = tables.call(name, args, timeout=10)
                serialized = encoded(response)
                trace.append(
                    {
                        "tool": name,
                        "arguments": args,
                        "response": response,
                        "response_characters": len(serialized),
                        "response_utf8_bytes": len(serialized.encode()),
                        "response_sha256": digest(serialized.encode()),
                        "latency_seconds": time.monotonic() - started,
                    }
                )
                return response

            ranks = None
            if condition == "window_oracle":
                response = call(
                    "read_table",
                    {
                        "source_id": protocol["source_id"],
                        "table_id": case["oracle_table_id"],
                        "row_indices": case["oracle_row_indices"],
                    },
                )
            else:
                search = call(
                    "search_tables", {"source_id": protocol["source_id"], "query": case["question"]}
                )
                hits = search.get("results", [])
                ranks = {
                    str(k): any(hit["table_id"] == fixture["table_id"] for hit in hits[:k])
                    for k in (1, 3, 5)
                }
                if hits:
                    response = call(
                        "read_table",
                        {
                            "source_id": protocol["source_id"],
                            "table_id": hits[0]["table_id"],
                            "row_indices": hits[0]["matched_row_indices"][:3],
                        },
                    )
                else:
                    response = {"error": "No search hits; no read attempted"}
            rows.append(
                {
                    "id": case["id"],
                    "expected_table_present_at_k": ranks,
                    "grading": grade_table_read(
                        fixture,
                        sidecar,
                        response,
                        manifest_sha256=digest((corpus / "sources.json").read_bytes()),
                    ),
                    "trace": trace,
                }
            )
        report["conditions"][condition] = {
            "task_denominator": len(cases),
            "required_context_present_count": sum(
                row["grading"]["required_context_present"] for row in rows
            ),
            "association_correctness": "not_measured",
            "typed_answer_correctness": "not_measured",
            "agent_selection_quality": "not_measured",
            "tasks": rows,
        }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "fixtures", "corpus", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.protocol, args.fixtures, args.corpus, args.output)
    print(
        json.dumps(
            {
                name: {
                    key: result[key]
                    for key in ("task_denominator", "required_context_present_count")
                }
                for name, result in report["conditions"].items()
            }
        )
    )


if __name__ == "__main__":
    main()
