"""Frozen ranked-parent read execution and separate replay-before-label grading."""

import argparse
import copy
import json
import os
import tempfile
from pathlib import Path

from eval.scripts.table_assessment_run import _load_object, _require_exact_keys, runtime_digest
from provenance.benchmarks import canonical_hash, load_bundle
from provenance.bounded_read import POLICY, read_ranked_passages
from provenance.evidence_coverage import coverage, digest
from provenance.source_quality import evaluate_corpus
from provenance.sources import Sources


def _write(path, value):
    temporary = path.with_suffix(".pending")
    with temporary.open("w") as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def _freeze(protocol_path, prepared, corpus, report_path):
    protocol_path, prepared, corpus, report_path = map(
        Path, [protocol_path, prepared, corpus, report_path]
    )
    raw = protocol_path.read_bytes()
    protocol = _load_object(raw, "Read protocol")
    _require_exact_keys(
        protocol,
        {
            "version",
            "policy",
            "runtime_sha256",
            "prepared_files_sha256",
            "corpus_manifest_sha256",
            "corpus_binding_sha256",
            "report_sha256",
            "plan_sha256",
            "packets_sha256",
        },
        "Read protocol",
    )
    if protocol["version"] != "parent-read-protocol-v1" or protocol["policy"] != POLICY:
        raise ValueError("Unsupported read protocol")
    _require_exact_keys(
        protocol["prepared_files_sha256"],
        {"manifest.json", "tasks.json", "inputs.json"},
        "Prepared hashes",
    )

    def verify():
        expected = {
            prepared / name: value for name, value in protocol["prepared_files_sha256"].items()
        }
        expected.update(
            {
                corpus / "sources.json": protocol["corpus_manifest_sha256"],
                corpus / "benchmark_binding.json": protocol["corpus_binding_sha256"],
                report_path: protocol["report_sha256"],
            }
        )
        if (
            protocol_path.read_bytes() != raw
            or runtime_digest() != protocol["runtime_sha256"]
            or any(digest(path) != value for path, value in expected.items())
        ):
            raise ValueError("Read frozen identity mismatch")
        Sources(corpus)

    verify()
    return protocol, verify


def _replay(prepared, corpus, report_path):
    report = _load_object(Path(report_path).read_bytes(), "Search report")
    replay = evaluate_corpus(
        load_bundle(prepared),
        corpus,
        source_scope=report.get("source_scope", "selected_corpus"),
        query_policy=report.get("query_policy", "original-question-v1"),
        include_snippets=True,
    )
    stripped = copy.deepcopy(replay)
    for row in stripped["tasks"]:
        for hit in row["retrieved_hits"]:
            del hit["snippet"]
    if canonical_hash(stripped) != canonical_hash(report):
        raise ValueError("Search report does not replay exactly")
    return [
        {
            "id": row["id"],
            "hits": [
                {key: hit[key] for key in ["source_id", "start_line", "end_line"]}
                for hit in row["retrieved_hits"]
            ],
        }
        for row in replay["tasks"]
    ]


def run(protocol_path, prepared, corpus, report_path, output_dir):
    protocol, verify = _freeze(protocol_path, prepared, corpus, report_path)
    plan = _replay(prepared, corpus, report_path)
    if canonical_hash(plan) != protocol["plan_sha256"]:
        raise ValueError("Projected plan mismatch")
    verify()
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=False)
    result = {
        "version": "parent-read-run-v1",
        "protocol_sha256": digest(protocol_path),
        "status": "pending",
        "cases": [
            {"id": row["id"], "status": "pending", "journal": f"case-{i}.jsonl"}
            for i, row in enumerate(plan)
        ],
    }
    _write(output_dir / "run.json", result)
    try:
        for row, case in zip(plan, result["cases"], strict=True):
            case["status"] = "running"
            _write(output_dir / "run.json", result)
            case["result"] = read_ranked_passages(
                Sources(corpus), row["hits"], output_dir / case["journal"]
            )
            case["status"] = "complete"
            case["journal_sha256"] = digest(output_dir / case["journal"])
            _write(output_dir / "run.json", result)
        verify()
        result["status"] = "complete"
        _write(output_dir / "run.json", result)
    except BaseException as error:
        result["status"] = "aborted"
        result["error_type"] = type(error).__name__
        _write(output_dir / "run.json", result)
        raise
    return result


def grade(protocol_path, prepared, corpus, report_path, packets_path, run_dir, output):
    output, run_dir, packets_path = map(Path, [output, run_dir, packets_path])
    if output.exists():
        raise ValueError("Grade output already exists")
    protocol, verify = _freeze(protocol_path, prepared, corpus, report_path)
    saved_raw = (run_dir / "run.json").read_bytes()
    saved = _load_object(saved_raw, "Read run")
    # Re-run calls into temporary journals; never open packet labels before equality.
    with tempfile.TemporaryDirectory() as temporary:
        replay_dir = Path(temporary) / "replay"
        replay = run(protocol_path, prepared, corpus, report_path, replay_dir)
        if canonical_hash(saved) != canonical_hash(replay):
            raise ValueError("Read run does not replay exactly")
        inventory = {"run.json", *(case["journal"] for case in replay["cases"])}
        if {p.name for p in run_dir.iterdir()} != inventory:
            raise ValueError("Read journal inventory mismatch")
        journal_bytes = {}
        for case in replay["cases"]:
            name = case["journal"]
            journal_bytes[name] = (run_dir / name).read_bytes()
            if journal_bytes[name] != (replay_dir / name).read_bytes():
                raise ValueError("Read journal does not replay exactly")
    if digest(packets_path) != protocol["packets_sha256"]:
        raise ValueError("Packet hash mismatch")
    packets = _load_object(packets_path.read_bytes(), "Read packets")
    _require_exact_keys(
        packets, {"version", "corpus_manifest_sha256", "sources", "cases"}, "Read packets"
    )
    sources = Sources(corpus)
    if (
        packets["version"] != "pdf-evidence-components-v1"
        or packets["corpus_manifest_sha256"] != protocol["corpus_manifest_sha256"]
    ):
        raise ValueError("Packet version or corpus mismatch")
    permitted = {row["id"]: row["context"]["doc_name"] for row in load_bundle(prepared)["inputs"]}
    if any(permitted.get(c["id"]) != c["source_id"] for c in packets["cases"]):
        raise ValueError("Packet source differs from declared document")
    if set(packets["sources"]) != {c["source_id"] for c in packets["cases"]}:
        raise ValueError("Packet source bindings mismatch")
    for sid, binding in packets["sources"].items():
        if binding != {k: sources.documents[sid].get(k) for k in ["original_sha256", "sha256"]}:
            raise ValueError("Packet source identity mismatch")
    rows = []
    for case in saved["cases"]:
        hits = []
        for record in case["result"]["records"]:
            response = record["response"]
            hits.append(
                {
                    **record["request"],
                    "snippet": "\n".join(line["text"] for line in response["lines"])
                    if response
                    else "",
                    "snippet_locator": response["locator"]
                    if response
                    else f"L{record['request']['start_line']}",
                }
            )
        rows.append({"id": case["id"], "retrieved_hits": hits})
    cases = coverage(packets["cases"], rows, sources)
    for case in cases:
        case["coverage"]["returned_reads"] = case["coverage"].pop("returned_snippets")
    result = {
        "version": "parent-read-grade-v1",
        "protocol_sha256": digest(protocol_path),
        "run_sha256": digest(run_dir / "run.json"),
        "selected_denominator": len(cases),
        "cases": cases,
        "semantic_correctness": "not_measured",
        "replay_verified": True,
    }
    result["summary"] = {
        channel: {
            f"top_{k}_complete_count": sum(
                c["coverage"][channel][f"top_{k}"]["complete"] for c in cases
            )
            for k in [1, 3, 5]
        }
        for channel in ["parent_passage_opportunity", "returned_reads"]
    }
    verify()
    if (
        {p.name for p in run_dir.iterdir()} != inventory
        or (run_dir / "run.json").read_bytes() != saved_raw
        or digest(packets_path) != protocol["packets_sha256"]
        or any((run_dir / name).read_bytes() != raw for name, raw in journal_bytes.items())
    ):
        raise ValueError("Grading inputs changed")
    with output.open("x") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "grade"])
    for name in ["protocol", "prepared", "corpus", "report", "output"]:
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--packets")
    parser.add_argument("--run-dir")
    args = parser.parse_args()
    common = [args.protocol, args.prepared, args.corpus, args.report]
    if args.action == "run":
        run(*common, args.output)
    elif args.packets and args.run_dir:
        grade(*common, args.packets, args.run_dir, args.output)
    else:
        parser.error("grade requires --packets and --run-dir")


if __name__ == "__main__":
    main()
