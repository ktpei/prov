"""Frozen six-case retrieval/retention comparison with replay before packet grading."""

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path

from eval.scripts.parent_read_assessment import _write
from eval.scripts.table_assessment_run import _load_object, _require_exact_keys, runtime_digest
from provenance.bounded_read import read_ranked_passages
from provenance.context import project_messages
from provenance.evidence_coverage import coverage, digest
from provenance.sources import Sources

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PREPARED = ROOT / "runs/financebench-context-v1-preparation/prepared"
CORPUS = ROOT / "runs/financebench-context-v1-preparation/corpus"
PACKETS = HERE / "annotation/packets.json"
BASE = ROOT / "eval/reports/context-retention-2026-11-16/analyze.py"
CHALLENGER = ROOT / "eval/reports/context-priority-2026-11-16/analyze.py"
POLICIES = ["production-newest-first", "earlier-optional-results-first-v1"]


def _paths():
    paths = {
        "driver": Path(__file__),
        "plan": HERE / "comparison-plan.md",
        "selection": HERE / "selection.json",
        "baseline_analysis": BASE,
        "challenger_analysis": CHALLENGER,
        "corpus_manifest": CORPUS / "sources.json",
        "corpus_binding": CORPUS / "benchmark_binding.json",
    }
    paths.update(
        {f"prepared/{n}": PREPARED / n for n in ["manifest.json", "tasks.json", "inputs.json"]}
    )
    paths.update({f"annotation/{p.name}": p for p in (HERE / "annotation").iterdir()})
    return paths


def _freeze(path):
    path = Path(path)
    raw = path.read_bytes()
    protocol = _load_object(raw, "Comparison protocol")
    _require_exact_keys(
        protocol,
        {"version", "limit", "policies", "case_ids", "runtime_sha256", "files"},
        "Comparison protocol",
    )
    if (
        protocol["version"] != "financebench-context-comparison-v1"
        or protocol["limit"] != 32000
        or protocol["policies"] != POLICIES
    ):
        raise ValueError("Unsupported comparison protocol")
    ids = protocol["case_ids"]
    if (
        not isinstance(ids, list)
        or len(ids) != 6
        or any(not isinstance(i, str) for i in ids)
        or len(set(ids)) != 6
    ):
        raise ValueError("Expected six distinct frozen cases")

    def verify():
        paths = _paths()
        if (
            path.read_bytes() != raw
            or runtime_digest() != protocol["runtime_sha256"]
            or set(paths) != set(protocol["files"])
        ):
            raise ValueError("Comparison frozen identity mismatch")
        if any(digest(p) != protocol["files"][name] for name, p in paths.items()):
            raise ValueError("Comparison frozen file mismatch")
        Sources(CORPUS)  # Checks every original and native-text identity.

    verify()
    return protocol, verify


def _module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _project(baseline, challenger, question, search, records):
    if len(records) > 5 or any(
        type(r.get("rank")) is not int
        or r["rank"] != i
        or r.get("status") not in {"returned", "failed"}
        for i, r in enumerate(records, 1)
    ):
        raise ValueError("Invalid ordered read records")
    if baseline.project_messages is not project_messages:
        raise ValueError("Unexpected baseline projector")
    left = baseline.snapshots(question, search, records)
    try:
        baseline.project_messages = challenger.project_messages
        right = baseline.snapshots(question, search, records)
    finally:
        baseline.project_messages = project_messages
    if any(left[k]["canonical_sha256"] != right[k]["canonical_sha256"] for k in left):
        raise ValueError("Policy histories differ")
    return dict(zip(POLICIES, [left, right], strict=True))


def run(protocol_path, output_dir):
    protocol, verify = _freeze(protocol_path)
    inputs = json.loads((PREPARED / "inputs.json").read_bytes())
    if [t["id"] for t in inputs] != protocol["case_ids"] or len(
        {t["context"]["doc_name"] for t in inputs}
    ) != 6:
        raise ValueError("Prepared case order or document denominator differs")
    baseline, challenger = (
        _module(BASE, "comparison_baseline"),
        _module(CHALLENGER, "comparison_challenger"),
    )
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=False)
    state = {
        "version": "financebench-context-comparison-run-v1",
        "protocol_sha256": digest(protocol_path),
        "status": "pending",
        "cases": [
            {
                "id": t["id"],
                "source_id": t["context"]["doc_name"],
                "status": "pending",
                "journal": f"case-{i}.jsonl",
            }
            for i, t in enumerate(inputs)
        ],
    }
    _write(output_dir / "run.json", state)
    try:
        for task, case in zip(inputs, state["cases"], strict=True):
            case["status"] = "search_started"
            _write(output_dir / "run.json", state)
            sources = Sources(CORPUS)
            sid = case["source_id"]
            sources.documents = {sid: sources.documents[sid]}
            search = sources.search(task["question"], timeout=1)
            case["search"] = search
            case["status"] = "search_saved"
            _write(output_dir / "run.json", state)
            hits = [
                {"source_id": h["id"], "start_line": h["start_line"], "end_line": h["end_line"]}
                for h in search["results"]
            ]
            case["reads"] = read_ranked_passages(sources, hits, output_dir / case["journal"])
            case["journal_sha256"] = digest(output_dir / case["journal"])
            case["status"] = "reads_saved"
            _write(output_dir / "run.json", state)
            case["conditions"] = _project(
                baseline, challenger, task["question"], search, case["reads"]["records"]
            )
            case["status"] = "complete"
            _write(output_dir / "run.json", state)
        verify()
        if set(_inventory(output_dir)) != {
            "run.json",
            *(c["journal"] for c in state["cases"]),
        } or any(digest(output_dir / c["journal"]) != c["journal_sha256"] for c in state["cases"]):
            raise ValueError("Execution journal inventory changed")
        state["status"] = "complete"
        _write(output_dir / "run.json", state)
        if (output_dir / "run.json").read_bytes() != _encoded(state):
            raise ValueError("Execution output changed")
    except BaseException as error:
        state.update(status="aborted", error_type=type(error).__name__)
        _write(output_dir / "run.json", state)
        raise
    return state


def _encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def _inventory(directory):
    return {p.name: p.read_bytes() for p in Path(directory).iterdir()}


def grade(protocol_path, run_dir, output):
    protocol, verify = _freeze(protocol_path)
    run_dir, output = Path(run_dir), Path(output)
    if output.exists() or output.resolve().is_relative_to(run_dir.resolve()):
        raise ValueError("Grade output exists or would alter run inventory")
    saved = _inventory(run_dir)
    with tempfile.TemporaryDirectory() as temporary:
        replay_dir = Path(temporary) / "replay"
        replay = run(protocol_path, replay_dir)
        if saved != _inventory(replay_dir):
            raise ValueError("Run, snapshots or journals do not replay exactly")
    verify()
    # Hash-only access above; packet JSON is opened only after BOTH conditions replay.
    packets = _load_object(PACKETS.read_bytes(), "Comparison packets")
    _require_exact_keys(
        packets, {"version", "corpus_manifest_sha256", "sources", "cases"}, "Comparison packets"
    )
    sources = Sources(CORPUS)
    if packets["version"] != "pdf-evidence-components-v1" or packets[
        "corpus_manifest_sha256"
    ] != digest(CORPUS / "sources.json"):
        raise ValueError("Packet corpus binding differs")
    permitted = {c["id"]: c["source_id"] for c in replay["cases"]}
    if any(permitted.get(c["id"]) != c["source_id"] for c in packets["cases"]) or set(
        packets["sources"]
    ) != set(permitted.values()):
        raise ValueError("Packet declared-source binding differs")
    for sid, binding in packets["sources"].items():
        if binding != {k: sources.documents[sid].get(k) for k in ["original_sha256", "sha256"]}:
            raise ValueError("Packet source identity differs")
    result = {
        "version": "financebench-context-comparison-grade-v1",
        "protocol_sha256": digest(protocol_path),
        "run_sha256": digest(run_dir / "run.json"),
        "selected_denominator": 6,
        "mapped_denominator": sum(c["disposition"] == "mapped" for c in packets["cases"]),
        "semantic_correctness": "not_measured",
        "replay_verified": True,
        "conditions": {},
        "paired": {},
    }
    result["operations"] = {
        "completed_cases": len(replay["cases"]),
        "search_calls": len(replay["cases"]),
        "read_attempts": sum(len(c["reads"]["records"]) for c in replay["cases"]),
        "failed_reads": sum(
            r["status"] == "failed" for c in replay["cases"] for r in c["reads"]["records"]
        ),
        "truncated_reads": sum(
            r.get("truncated", False) for c in replay["cases"] for r in c["reads"]["records"]
        ),
        "replay_search_calls": len(replay["cases"]),
        "replay_read_attempts": sum(len(c["reads"]["records"]) for c in replay["cases"]),
    }
    search_rows, read_rows = [], []
    for case in replay["cases"]:
        search_rows.append(
            {
                "id": case["id"],
                "retrieved_hits": [{**h, "source_id": h["id"]} for h in case["search"]["results"]],
            }
        )
        read_rows.append(
            {
                "id": case["id"],
                "retrieved_hits": [
                    {
                        **r["request"],
                        "snippet": "\n".join(line["text"] for line in r["response"]["lines"])
                        if r["status"] == "returned"
                        else "",
                        "snippet_locator": r["response"]["locator"]
                        if r["status"] == "returned"
                        else f"L{r['request']['start_line']}",
                    }
                    for r in case["reads"]["records"]
                ],
            }
        )
    result["delivery"] = {
        "search": coverage(packets["cases"], search_rows, sources),
        "read": coverage(packets["cases"], read_rows, sources),
    }
    for policy in POLICIES:
        result["conditions"][policy] = {}
        for k in [1, 3, 5]:
            key = f"top_{k}"
            rows = [
                {"id": c["id"], "retrieved_hits": c["conditions"][policy][key]["read_hits"]}
                for c in replay["cases"]
            ]
            measured = coverage(packets["cases"], rows, sources)
            result["conditions"][policy][key] = {
                "complete_count": sum(
                    c["coverage"]["returned_snippets"][key]["complete"] for c in measured
                ),
                "blocked_count": sum(
                    c["conditions"][policy][key]["status"] == "blocked" for c in replay["cases"]
                ),
                "cases": [
                    {"id": c["id"], **c["coverage"]["returned_snippets"][key]} for c in measured
                ],
            }
    for k in [1, 3, 5]:
        key = f"top_{k}"
        pairs = list(zip(*(result["conditions"][p][key]["cases"] for p in POLICIES), strict=True))
        result["paired"][key] = {
            "wins": sum(b["complete"] and not a["complete"] for a, b in pairs),
            "losses": sum(a["complete"] and not b["complete"] for a, b in pairs),
            "ties": sum(a["complete"] == b["complete"] for a, b in pairs),
        }
    verify()
    if saved != _inventory(run_dir):
        raise ValueError("Grading inputs changed")
    with output.open("x") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if output.read_bytes() != _encoded(result):
        raise ValueError("Grade output changed")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "grade"])
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.action == "run":
        print(run(args.protocol, args.run_dir)["status"])
    else:
        if not args.output:
            parser.error("grade requires --output")
        print(json.dumps(grade(args.protocol, args.run_dir, args.output)["paired"]))
