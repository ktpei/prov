"""One-off frozen original-question context-retention analysis; no model calls."""

import argparse
import copy
import json
import tempfile
from pathlib import Path

from eval.scripts.parent_read_assessment import _freeze, run
from eval.scripts.table_assessment_run import _load_object, _require_exact_keys, runtime_digest
from provenance.benchmarks import canonical_hash, load_bundle
from provenance.context import project_messages, tool_result_chars
from provenance.controls import LimitReached
from provenance.evidence_coverage import coverage, digest
from provenance.sources import Sources

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
READ_ROOT = ROOT / "eval/reports/bounded-reading-2026-11-16"
RUN_ROOT = ROOT / "runs/bounded-reading-2026-11-16/original"
PREPARED = ROOT / "runs/benchmark-prepared/financebench-full-docs-v1"
CORPUS = ROOT / "runs/financebench-full-docs-v2"
REPORT = ROOT / "runs/financebench-source-quality-scoped-v1.json"
PACKETS = ROOT / "eval/reports/evidence-components-2026-11-16/packets.json"


def pair(name, call_id, arguments, response):
    return [
        {
            "type": "function_call",
            "call_id": call_id,
            "name": name,
            "arguments": json.dumps(arguments),
        },
        {"type": "function_call_output", "call_id": call_id, "output": json.dumps(response)},
    ]


def snapshots(question, search, records, limit=32000):
    history = [{"role": "user", "content": question}]
    history += pair("search", "search-1", {"query": question}, search)
    for record in records:
        result = (
            record["response"] if record["status"] == "returned" else {"error": record["error"]}
        )
        history += pair("read_source", f"read-{record['rank']}", record["request"], result)
    snapshot = copy.deepcopy(history)
    outputs = {}
    for k in [1, 3, 5]:
        prefix = history[: 3 + 2 * min(k, len(records))]
        item = {
            "attempted_read_slots": min(k, len(records)),
            "characters_before": tool_result_chars(prefix),
            "retained_read_ranks": [],
            "omitted_read_ranks": [],
            "failed_read_ranks": [],
            "read_hits": [],
        }
        try:
            projected = project_messages(prefix, max_tool_result_chars=limit)
        except LimitReached as error:
            item.update(
                status="blocked", reason=str(error), characters_after=None, projected_sha256=None
            )
            visible = {}
        else:
            item.update(
                status="projected",
                characters_after=tool_result_chars(projected),
                projected_sha256=canonical_hash(projected),
            )
            visible = {
                m["call_id"]: m["output"]
                for m in projected
                if m.get("type") == "function_call_output"
            }
        item["canonical_sha256"] = canonical_hash(prefix)
        for record in records[:k]:
            response = record["response"]
            successful = record["status"] == "returned"
            retained = successful and visible.get(f"read-{record['rank']}") == json.dumps(response)
            if not successful:
                item["failed_read_ranks"].append(record["rank"])
            else:
                item["retained_read_ranks" if retained else "omitted_read_ranks"].append(
                    record["rank"]
                )
            item["read_hits"].append(
                {
                    **record["request"],
                    "snippet": "\n".join(line["text"] for line in response["lines"])
                    if retained
                    else "",
                    "snippet_locator": response["locator"]
                    if retained
                    else f"L{record['request']['start_line']}",
                }
            )
        outputs[f"top_{k}"] = item
    if history != snapshot:
        raise ValueError("Projection changed canonical history")
    return outputs


def execute(protocol_path, output):
    protocol_path, output = Path(protocol_path), Path(output)
    if output.exists():
        raise ValueError("Analysis output exists")
    raw = protocol_path.read_bytes()
    protocol = _load_object(raw, "Context protocol")
    _require_exact_keys(
        protocol,
        {
            "version",
            "limit",
            "analysis_sha256",
            "runtime_sha256",
            "read_protocol_sha256",
            "run_sha256",
            "journals",
            "packets_sha256",
        },
        "Context protocol",
    )
    if protocol["version"] != "context-retention-protocol-v1" or protocol["limit"] != 32000:
        raise ValueError("Unsupported context protocol")

    def verify(include_packets=False):
        expected = {
            Path(__file__): protocol["analysis_sha256"],
            READ_ROOT / "original-protocol.json": protocol["read_protocol_sha256"],
            RUN_ROOT / "run.json": protocol["run_sha256"],
        }
        expected.update({RUN_ROOT / name: value for name, value in protocol["journals"].items()})
        if include_packets:
            expected[PACKETS] = protocol["packets_sha256"]
        if (
            protocol_path.read_bytes() != raw
            or runtime_digest() != protocol["runtime_sha256"]
            or any(digest(path) != value for path, value in expected.items())
        ):
            raise ValueError("Frozen context identity mismatch")
        if {p.name for p in RUN_ROOT.iterdir()} != {"run.json", *protocol["journals"]}:
            raise ValueError("Journal inventory mismatch")
        read_protocol, read_verify = _freeze(
            READ_ROOT / "original-protocol.json", PREPARED, CORPUS, REPORT
        )
        read_verify()
        if read_protocol["packets_sha256"] != protocol["packets_sha256"]:
            raise ValueError("Packet identity differs from read experiment")

    verify()
    saved = json.loads((RUN_ROOT / "run.json").read_bytes())
    with tempfile.TemporaryDirectory() as temporary:
        replay_dir = Path(temporary) / "replay"
        replay = run(READ_ROOT / "original-protocol.json", PREPARED, CORPUS, REPORT, replay_dir)
        if canonical_hash(saved) != canonical_hash(replay):
            raise ValueError("Original read run replay mismatch")
        inventory = {"run.json", *(c["journal"] for c in replay["cases"])}
        if {p.name for p in RUN_ROOT.iterdir()} != inventory or set(
            protocol["journals"]
        ) != inventory - {"run.json"}:
            raise ValueError("Journal inventory mismatch")
        for name in protocol["journals"]:
            if (RUN_ROOT / name).read_bytes() != (replay_dir / name).read_bytes():
                raise ValueError("Read journal replay mismatch")
    inputs = load_bundle(PREPARED)["inputs"]
    cases = []
    for task, case in zip(inputs, saved["cases"], strict=True):
        if task["id"] != case["id"]:
            raise ValueError("Task order mismatch")
        sources = Sources(CORPUS)
        sid = task["context"]["doc_name"]
        sources.documents = {sid: sources.documents[sid]}
        search = sources.search(task["question"], timeout=1)
        projection = [
            {"source_id": h["id"], "start_line": h["start_line"], "end_line": h["end_line"]}
            for h in search["results"]
        ]
        if canonical_hash(projection) != canonical_hash(
            [r["request"] for r in case["result"]["records"]]
        ):
            raise ValueError("Search/read plan mismatch")
        cases.append(
            {
                "id": case["id"],
                "snapshots": snapshots(task["question"], search, case["result"]["records"]),
            }
        )
    # Every projection is fixed before packet bytes are opened.
    verify(include_packets=True)
    packets = _load_object(PACKETS.read_bytes(), "Context packets")
    _require_exact_keys(
        packets, {"version", "corpus_manifest_sha256", "sources", "cases"}, "Context packets"
    )
    sources = Sources(CORPUS)
    if packets["version"] != "pdf-evidence-components-v1" or packets[
        "corpus_manifest_sha256"
    ] != digest(CORPUS / "sources.json"):
        raise ValueError("Packet version or corpus mismatch")
    permitted = {task["id"]: task["context"]["doc_name"] for task in inputs}
    if any(permitted.get(case["id"]) != case["source_id"] for case in packets["cases"]):
        raise ValueError("Packet source differs from declared document")
    if set(packets["sources"]) != {case["source_id"] for case in packets["cases"]}:
        raise ValueError("Packet source bindings mismatch")
    for sid, binding in packets["sources"].items():
        if binding != {
            key: sources.documents[sid].get(key) for key in ["original_sha256", "sha256"]
        }:
            raise ValueError("Packet source identity mismatch")
    for k in [1, 3, 5]:
        rows = [
            {"id": c["id"], "retrieved_hits": c["snapshots"][f"top_{k}"]["read_hits"]}
            for c in cases
        ]
        measured = coverage(packets["cases"], rows, sources)
        for case, result in zip(cases, measured, strict=True):
            case["snapshots"][f"top_{k}"]["component_coverage"] = result["coverage"][
                "returned_snippets"
            ][f"top_{k}"]
    result = {
        "version": "context-retention-result-v1",
        "protocol_sha256": digest(protocol_path),
        "selected_denominator": len(cases),
        "cases": cases,
        "semantic_correctness": "not_measured",
        "summary": {
            f"top_{k}_complete_count": sum(
                c["snapshots"][f"top_{k}"]["component_coverage"]["complete"] for c in cases
            )
            for k in [1, 3, 5]
        },
    }
    verify(include_packets=True)
    with output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.protocol, args.output)["summary"]))
