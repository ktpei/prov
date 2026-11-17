"""Shared-pool page ranking with whole-run replay before evidence grading."""

import argparse
import importlib.util
import json
import os
import platform
import sys
import tempfile
import time
from pathlib import Path

from eval.scripts.parent_read_assessment import _write
from eval.scripts.table_assessment_run import _load_object, _require_exact_keys, runtime_digest
from provenance.benchmarks import canonical_hash
from provenance.bounded_read import read_ranked_passages
from provenance.evidence_coverage import coverage, digest, span
from provenance.page_ranking import compare_page_ranking
from provenance.sources import Sources

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT / "eval/assessments/financebench-context-v1"
HISTORY = ROOT / "runs/financebench-compact-read-v1/pdf-returned-pages-v1"
HISTORY_PROTOCOL = ROOT / "eval/assessments/financebench-compact-read-v1/inner-protocol.json"
RESERVATION = ROOT / "eval/assessments/financebench-page-validation-v1"
BRANCHES = ["control", "challenger"]
PARAMETERS = {
    "candidate_limit": 25,
    "read_limit": 5,
    "rrf_constant": 60,
    "context_limit": 32000,
    "read_extraction_version": "pdf-returned-pages-v1",
    "retrieval_version": "bm25-v2",
    "ranking_version": "page-rrf-ablation-v1",
}


def _base():
    spec = importlib.util.spec_from_file_location("page_comparison", BASE / "compare.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _environment():
    if os.environ.get("PYTHONHASHSEED") != "0" or sys.flags.hash_randomization != 0:
        raise ValueError("Start Python with PYTHONHASHSEED=0 before assessment")
    return {
        "python": platform.python_version(),
        "implementation": sys.implementation.name,
        "hash_seed": "0",
    }


def _paths():
    paths = dict(_base()._paths())
    paths.update(
        {"wrapper": Path(__file__), "experiment_plan": HERE / "plan.md", "lock": ROOT / "uv.lock"}
    )
    paths.update(
        {
            f"reservation/{name}": RESERVATION / name
            for name in [
                "plan.md",
                "reserve.py",
                "reservation.json",
                "exposure-audit.json",
                "progress.md",
            ]
        }
    )
    paths.update({f"history/{p.name}": p for p in HISTORY.iterdir()})
    return paths


def _freeze(path):
    path = Path(path)
    raw = path.read_bytes()
    protocol = _load_object(raw, "Page ranking protocol")
    _require_exact_keys(
        protocol,
        {"version", "parameters", "environment", "case_ids", "runtime_sha256", "files"},
        "Page ranking protocol",
    )
    if protocol["version"] != "page-ranking-assessment-v1" or canonical_hash(
        protocol["parameters"]
    ) != canonical_hash(PARAMETERS):
        raise ValueError("Unsupported page ranking protocol")
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
            or _environment() != protocol["environment"]
            or runtime_digest() != protocol["runtime_sha256"]
            or set(paths) != set(protocol["files"])
            or any(digest(p) != protocol["files"][key] for key, p in paths.items())
        ):
            raise ValueError("Page ranking frozen identity mismatch")
        Sources(_base().CORPUS)

    verify()
    return protocol, verify


def _inventory(directory):
    return {p.name: digest(p) for p in Path(directory).iterdir()}


def _same_file(path, value):
    if Path(path).read_bytes() != _base()._encoded(value):
        raise ValueError("Written artifact differs from returned object")


def _sources(corpus, sid):
    sources = Sources(corpus, read_extraction_version=PARAMETERS["read_extraction_version"])
    sources.documents = {sid: sources.documents[sid]}
    return sources


def _compatibility(case, historical, directory):
    if case["id"] != historical["id"] or case["source_id"] != historical["source_id"]:
        raise ValueError("Historical case binding differs")
    control = case["branches"]["control"]
    for key in ["search", "reads", "conditions"]:
        if canonical_hash(control[key]) != canonical_hash(historical[key]):
            raise ValueError(f"Control {key} differs from compact history")
    if digest(directory / control["journal"]) != digest(HISTORY / historical["journal"]):
        raise ValueError("Control journal differs from compact history")


def run(protocol_path, run_dir):
    protocol, verify = _freeze(protocol_path)
    base = _base()
    inputs = json.loads((base.PREPARED / "inputs.json").read_bytes())
    history = json.loads((HISTORY / "run.json").read_bytes())
    if (
        [t["id"] for t in inputs] != protocol["case_ids"]
        or len({t["context"]["doc_name"] for t in inputs}) != 6
        or [c["id"] for c in history["cases"]] != protocol["case_ids"]
        or history["status"] != "complete"
        or history["protocol_sha256"] != digest(HISTORY_PROTOCOL)
    ):
        raise ValueError("Case order or history differs")
    run_dir = Path(run_dir)
    run_dir.mkdir(exist_ok=False)
    directory = run_dir / "deterministic"
    directory.mkdir()
    state = {
        "version": "page-ranking-run-v1",
        "protocol_sha256": digest(protocol_path),
        "status": "pending",
        "cases": [
            {
                "id": t["id"],
                "source_id": t["context"]["doc_name"],
                "status": "pending",
                "branches": {
                    b: {"status": "pending", "journal": f"case-{i}-{b}.jsonl"} for b in BRANCHES
                },
            }
            for i, t in enumerate(inputs)
        ],
    }
    _write(directory / "run.json", state)
    timings = []
    baseline = base._module(base.BASE, "page_baseline_projection")
    challenger = base._module(base.CHALLENGER, "page_challenger_projection")
    try:
        for task, case, old in zip(inputs, state["cases"], history["cases"], strict=True):
            case["status"] = "ranking_started"
            _write(directory / "run.json", state)
            sources = _sources(base.CORPUS, case["source_id"])
            start = time.perf_counter()
            case["ranking"] = compare_page_ranking(sources, task["question"])
            case["scoring_work"] = {
                "eligible_passages": sum(
                    p["source_id"] in sources.documents for p in sources.passages
                ),
                "physical_pages": len(case["ranking"]["page_ranks"]),
            }
            timing = {
                "id": case["id"],
                "ranking_seconds": time.perf_counter() - start,
                "branches": {},
            }
            timings.append(timing)
            case["status"] = "ranking_saved"
            _write(directory / "run.json", state)
            for name in BRANCHES:
                branch = case["branches"][name]
                branch["search"] = {"results": case["ranking"][name], "mode": "frozen_corpus"}
                branch["status"] = "search_saved"
                _write(directory / "run.json", state)
                sources = _sources(base.CORPUS, case["source_id"])
                hits = [
                    {"source_id": h["id"], "start_line": h["start_line"], "end_line": h["end_line"]}
                    for h in branch["search"]["results"]
                ]
                start = time.perf_counter()
                branch["reads"] = read_ranked_passages(sources, hits, directory / branch["journal"])
                timing["branches"][name] = {"read_seconds": time.perf_counter() - start}
                branch["journal_sha256"] = digest(directory / branch["journal"])
                branch["conditions"] = base._project(
                    baseline,
                    challenger,
                    task["question"],
                    branch["search"],
                    branch["reads"]["records"],
                )
                branch["status"] = "complete"
                _write(directory / "run.json", state)
            _compatibility(case, old, directory)
            case["status"] = "complete"
            _write(directory / "run.json", state)
        verify()
        expected = {
            "run.json",
            *(b["journal"] for c in state["cases"] for b in c["branches"].values()),
        }
        if set(_inventory(directory)) != expected or any(
            digest(directory / b["journal"]) != b["journal_sha256"]
            for c in state["cases"]
            for b in c["branches"].values()
        ):
            raise ValueError("Execution inventory changed")
        state["status"] = "complete"
        _write(directory / "run.json", state)
        _same_file(directory / "run.json", state)
        deterministic = _inventory(directory)
        telemetry = {"version": "page-ranking-timing-v1", "cases": timings}
        _write(run_dir / "telemetry.json", telemetry)
        _same_file(run_dir / "telemetry.json", telemetry)
        receipt = {
            "version": "page-ranking-receipt-v1",
            "protocol_sha256": digest(protocol_path),
            "deterministic": deterministic,
            "telemetry_sha256": digest(run_dir / "telemetry.json"),
        }
        _write(run_dir / "receipt.json", receipt)
        _same_file(run_dir / "receipt.json", receipt)
        _validated_inventory(run_dir, protocol_path)
        _same_file(directory / "run.json", state)
        verify()
    except BaseException as error:
        state.update(status="aborted", error_type=type(error).__name__)
        _write(directory / "run.json", state)
        raise
    return state


def _validated_inventory(run_dir, protocol_path):
    run_dir = Path(run_dir)
    if {p.name for p in run_dir.iterdir()} != {"deterministic", "receipt.json", "telemetry.json"}:
        raise ValueError("Unexpected assessment inventory")
    receipt = _load_object((run_dir / "receipt.json").read_bytes(), "Run receipt")
    _require_exact_keys(
        receipt, {"version", "protocol_sha256", "deterministic", "telemetry_sha256"}, "Run receipt"
    )
    inventory = _inventory(run_dir / "deterministic")
    if (
        receipt["version"] != "page-ranking-receipt-v1"
        or receipt["protocol_sha256"] != digest(protocol_path)
        or receipt["deterministic"] != inventory
        or receipt["telemetry_sha256"] != digest(run_dir / "telemetry.json")
    ):
        raise ValueError("Run receipt binding differs")
    return {
        "receipt": digest(run_dir / "receipt.json"),
        "telemetry": receipt["telemetry_sha256"],
        "deterministic": inventory,
    }


def pool_coverage(cases, rows, sources):
    # Existing validator checks packet roles/alternatives and exact candidate spans.
    coverage(cases, [{"id": r["id"], "retrieved_hits": []} for r in rows], sources)
    result = []
    for case, row in zip(cases, rows, strict=True):
        hits = row["retrieved_hits"]
        if not isinstance(hits, list) or len(hits) > 25:
            raise ValueError("Pool exceeds frozen candidate limit")
        lines = sources.documents[case["source_id"]]["text"].splitlines()
        windows, identities = [], set()
        for hit in hits:
            if (
                not isinstance(hit, dict)
                or set(hit) != {"source_id", "start_line", "end_line", "snippet"}
                or hit["source_id"] != case["source_id"]
                or hit["snippet"] != ""
            ):
                raise ValueError("Invalid declared-source pool candidate")
            windows.append(span([hit["start_line"], hit["end_line"]], len(lines)))
            identity = (hit["source_id"], hit["start_line"], hit["end_line"])
            if identity in identities:
                raise ValueError("Duplicate pool candidate")
            identities.add(identity)
        available = set().union(*windows)
        alternatives = []
        for alternative in case["alternatives"]:
            presence = {
                role: set().union(*(span(s, len(lines)) for s in ranges)) <= available
                for role, ranges in alternative.items()
            }
            alternatives.append(
                {"components_present": presence, "complete": all(presence.values())}
            )
        result.append(
            {
                "id": case["id"],
                "disposition": case["disposition"],
                "candidate_count": len(hits),
                "measure": "candidate_pool_parent_opportunity",
                "complete": any(a["complete"] for a in alternatives),
                "alternatives": alternatives,
            }
        )
    return result


def grade(protocol_path, run_dir, output):
    protocol, verify = _freeze(protocol_path)
    run_dir, output = Path(run_dir), Path(output)
    if output.exists() or output.resolve().is_relative_to(run_dir.resolve()):
        raise ValueError("Grade output exists or would alter run")
    saved = _validated_inventory(run_dir, protocol_path)
    with tempfile.TemporaryDirectory() as temporary:
        replay_dir = Path(temporary) / "replay"
        replay = run(protocol_path, replay_dir)
        _same_file(replay_dir / "deterministic/run.json", replay)
        replay_inventory = _validated_inventory(replay_dir, protocol_path)
        if saved["deterministic"] != replay_inventory["deterministic"]:
            raise ValueError("Whole run does not replay exactly")
    verify()
    if _validated_inventory(run_dir, protocol_path) != saved:
        raise ValueError("Run changed before grading")
    # All shared rankings, branches, reads and projections have replayed before labels.
    base = _base()
    packets = _load_object(base.PACKETS.read_bytes(), "Page ranking packets")
    _require_exact_keys(
        packets, {"version", "corpus_manifest_sha256", "sources", "cases"}, "Page ranking packets"
    )
    sources = Sources(base.CORPUS)
    permitted = {c["id"]: c["source_id"] for c in replay["cases"]}
    if (
        packets["version"] != "pdf-evidence-components-v1"
        or packets["corpus_manifest_sha256"] != digest(base.CORPUS / "sources.json")
        or [c["id"] for c in packets["cases"]] != protocol["case_ids"]
        or set(packets["sources"]) != set(permitted.values())
        or any(permitted.get(c["id"]) != c["source_id"] for c in packets["cases"])
    ):
        raise ValueError("Packet case or source binding differs")
    for sid, binding in packets["sources"].items():
        if binding != {k: sources.documents[sid].get(k) for k in ["original_sha256", "sha256"]}:
            raise ValueError("Packet original/text identity differs")
    pool_rows = [
        {
            "id": c["id"],
            "retrieved_hits": [
                {
                    "source_id": h["source_id"],
                    "start_line": h["start_line"],
                    "end_line": h["end_line"],
                    "snippet": "",
                }
                for h in c["ranking"]["candidates"]
            ],
        }
        for c in replay["cases"]
    ]
    result = {
        "version": "page-ranking-grade-v1",
        "protocol_sha256": digest(protocol_path),
        "run_inventory": saved,
        "selected_denominator": 6,
        "mapped_denominator": sum(c["disposition"] == "mapped" for c in packets["cases"]),
        "replay_verified": True,
        "semantic_correctness": "not_measured",
        "pool_25": pool_coverage(packets["cases"], pool_rows, sources),
        "branches": {},
        "paired": {},
        "operations": {
            "shared_passage_scoring_passes": 6,
            "shared_page_scoring_passes": 6,
            "derived_search_responses": 12,
            "eligible_passages_scored": sum(
                c["scoring_work"]["eligible_passages"] for c in replay["cases"]
            ),
            "physical_pages_scored": sum(
                c["scoring_work"]["physical_pages"] for c in replay["cases"]
            ),
            "replay_shared_passage_scoring_passes": 6,
            "replay_shared_page_scoring_passes": 6,
        },
    }
    for name in BRANCHES:
        search_rows, read_rows = [], []
        branch_cases = [c["branches"][name] for c in replay["cases"]]
        for case, branch in zip(replay["cases"], branch_cases, strict=True):
            search_rows.append(
                {
                    "id": case["id"],
                    "retrieved_hits": [
                        {**h, "source_id": h["id"]} for h in branch["search"]["results"]
                    ],
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
                        for r in branch["reads"]["records"]
                    ],
                }
            )
        records = [r for b in branch_cases for r in b["reads"]["records"]]
        measured = {
            "search": coverage(packets["cases"], search_rows, sources),
            "read": coverage(packets["cases"], read_rows, sources),
            "conditions": {},
            "operations": {
                "read_attempts": len(records),
                "replay_read_attempts": len(records),
                "failed_reads": sum(r["status"] == "failed" for r in records),
                "truncated_reads": sum(r.get("truncated", False) for r in records),
            },
        }
        for policy in base.POLICIES:
            measured["conditions"][policy] = {}
            for k in [1, 3, 5]:
                key = f"top_{k}"
                rows = [
                    {"id": c["id"], "retrieved_hits": b["conditions"][policy][key]["read_hits"]}
                    for c, b in zip(replay["cases"], branch_cases, strict=True)
                ]
                observed = coverage(packets["cases"], rows, sources)
                measured["conditions"][policy][key] = {
                    "complete_count": sum(
                        c["coverage"]["returned_snippets"][key]["complete"] for c in observed
                    ),
                    "blocked_count": sum(
                        b["conditions"][policy][key]["status"] == "blocked" for b in branch_cases
                    ),
                    "cases": [
                        {"id": c["id"], **c["coverage"]["returned_snippets"][key]} for c in observed
                    ],
                }
        result["branches"][name] = measured
    for policy in base.POLICIES:
        result["paired"][policy] = {}
        for key in ["top_1", "top_3", "top_5"]:
            pairs = list(
                zip(
                    *(
                        result["branches"][name]["conditions"][policy][key]["cases"]
                        for name in BRANCHES
                    ),
                    strict=True,
                )
            )
            if any(a["id"] != b["id"] for a, b in pairs):
                raise ValueError("Paired case identity mismatch")
            result["paired"][policy][key] = {
                "wins": sum(b["complete"] and not a["complete"] for a, b in pairs),
                "losses": sum(a["complete"] and not b["complete"] for a, b in pairs),
                "ties": sum(a["complete"] == b["complete"] for a, b in pairs),
            }
    verify()
    if _validated_inventory(run_dir, protocol_path) != saved:
        raise ValueError("Grading inputs changed")
    with output.open("x") as handle:
        handle.write(base._encoded(result).decode())
    _same_file(output, result)
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
