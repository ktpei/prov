"""Mode-attributed wrapper around the immutable six-case comparison machinery."""

import argparse
import copy
import importlib.util
import json
from contextlib import contextmanager
from pathlib import Path

from eval.scripts.parent_read_assessment import _write
from eval.scripts.table_assessment_run import _load_object, _require_exact_keys, runtime_digest
from provenance.benchmarks import canonical_hash
from provenance.evidence_coverage import digest
from provenance.sources import Sources

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT / "eval/assessments/financebench-context-v1"
HISTORY = ROOT / "runs/financebench-context-v1-comparison"
HISTORICAL_GRADE = ROOT / "runs/financebench-context-v1-comparison-grade.json"
MODES = ["full-v1", "pdf-returned-pages-v1"]


def _base():
    spec = importlib.util.spec_from_file_location("compact_read_comparison", BASE / "compare.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _paths():
    paths = dict(_base()._paths())
    paths.update(
        {
            "wrapper": Path(__file__),
            "experiment_plan": HERE / "plan.md",
            "inner_protocol": HERE / "inner-protocol.json",
            "historical_protocol": BASE / "comparison-protocol.json",
            "historical_grade": HISTORICAL_GRADE,
        }
    )
    paths.update({f"historical/{p.name}": p for p in HISTORY.iterdir()})
    return paths


def _freeze(path):
    path = Path(path)
    raw = path.read_bytes()
    protocol = _load_object(raw, "Compact assessment protocol")
    _require_exact_keys(
        protocol, {"version", "modes", "runtime_sha256", "files"}, "Compact assessment protocol"
    )
    if protocol["version"] != "compact-read-assessment-v1" or protocol["modes"] != MODES:
        raise ValueError("Unsupported compact assessment")

    def verify():
        paths = _paths()
        if (
            path.read_bytes() != raw
            or runtime_digest() != protocol["runtime_sha256"]
            or set(paths) != set(protocol["files"])
            or any(digest(p) != protocol["files"][k] for k, p in paths.items())
        ):
            raise ValueError("Compact frozen identity mismatch")
        _base()._freeze(HERE / "inner-protocol.json")

    verify()
    return verify


@contextmanager
def _mode(mode, expected=None):
    if mode not in MODES:
        raise ValueError("Unknown assessment mode")
    module = _base()
    original = module.Sources
    if original is not Sources:
        raise ValueError("Unexpected source constructor")

    def factory(*args, **kwargs):
        source = original(*args, **kwargs, read_extraction_version=mode)
        if expected is not None:
            search = source.search

            def checked_search(*args, **kwargs):
                if len(source.documents) != 1:
                    raise ValueError("Search must have one declared document")
                sid = next(iter(source.documents))
                response = search(*args, **kwargs)
                if sid not in expected or canonical_hash(response) != canonical_hash(expected[sid]):
                    raise ValueError("Compact search differs before read dispatch")
                return response

            source.search = checked_search
        return source

    try:
        module.Sources = factory
        yield module
    finally:
        module.Sources = original


def _inventory(directory):
    return {p.name: digest(p) for p in Path(directory).iterdir()}


def _compatibility(full_dir):
    full_dir = Path(full_dir)
    actual = json.loads((full_dir / "run.json").read_bytes())
    historical = json.loads((HISTORY / "run.json").read_bytes())
    if actual["protocol_sha256"] != digest(HERE / "inner-protocol.json") or historical[
        "protocol_sha256"
    ] != digest(BASE / "comparison-protocol.json"):
        raise ValueError("Compatibility protocol attribution differs")
    normalized = copy.deepcopy(actual)
    normalized["protocol_sha256"] = historical["protocol_sha256"]
    if canonical_hash(normalized) != canonical_hash(historical):
        raise ValueError("Default run differs from history")
    old, new = _inventory(HISTORY), _inventory(full_dir)
    if set(old) != set(new) or any(old[n] != new[n] for n in old if n != "run.json"):
        raise ValueError("Default journals differ from history")
    return actual


def _same_evidence(full, compact):
    if [c["id"] for c in full["cases"]] != [c["id"] for c in compact["cases"]]:
        raise ValueError("Mode case order differs")
    for a, b in zip(full["cases"], compact["cases"], strict=True):
        if a["source_id"] != b["source_id"] or canonical_hash(a["search"]) != canonical_hash(
            b["search"]
        ):
            raise ValueError("Mode search differs")
        left, right = a["reads"]["records"], b["reads"]["records"]
        if len(left) != len(right):
            raise ValueError("Mode read denominator differs")
        for old, new in zip(left, right, strict=True):
            normalized = copy.deepcopy(new)
            if old["status"] == "returned" and new["status"] == "returned":
                original, projected = old["response"]["extraction"], new["response"]["extraction"]
                if (
                    isinstance(original, dict)
                    and original.get("diagnostics_version") == "pdf-extraction-diagnostics-v2"
                ):
                    pages = {line["original_location"]["page"] for line in new["response"]["lines"]}
                    metadata = copy.deepcopy(projected)
                    descriptor = metadata.pop("read_projection")
                    if canonical_hash(metadata["pages"]) != canonical_hash(
                        [p for p in original["pages"] if p["page"] in pages]
                    ):
                        raise ValueError("Projected page diagnostics differ")
                    metadata["pages"] = original["pages"]
                    if canonical_hash(metadata) != canonical_hash(original) or canonical_hash(
                        descriptor
                    ) != canonical_hash(
                        {
                            "version": MODES[1],
                            "scope": "Full-page diagnostics for physical pages present in returned lines; not excerpt counts.",
                            "retained_page_count": len(pages),
                            "omitted_page_count": original["page_count"] - len(pages),
                            "full_diagnostics_sha256": canonical_hash(original),
                            "full_diagnostics_location": {
                                "manifest": "sources.json",
                                "source_id": a["source_id"],
                                "field": "extraction",
                            },
                        }
                    ):
                        raise ValueError("Projected global diagnostics or provenance differ")
                elif canonical_hash(original) != canonical_hash(projected):
                    raise ValueError("Unsupported metadata changed")
                normalized["response"]["extraction"] = original
            if canonical_hash(normalized) != canonical_hash(old):
                raise ValueError("Evidence or read status changed across modes")
        if a["reads"]["policy"] != b["reads"]["policy"] or set(a["reads"]["budgets"]) != set(
            b["reads"]["budgets"]
        ):
            raise ValueError("Read policy or budget prefixes differ")
        for key, budget in b["reads"]["budgets"].items():
            expected = a["reads"]["budgets"][key]
            if canonical_hash(
                {k: v for k, v in budget.items() if k != "returned_json_bytes"}
            ) != canonical_hash({k: v for k, v in expected.items() if k != "returned_json_bytes"}):
                raise ValueError("Evidence budget changed across modes")


def run(protocol_path, output_dir):
    verify = _freeze(protocol_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=False)
    state = {
        "version": "compact-read-run-v1",
        "protocol_sha256": digest(protocol_path),
        "inner_protocol_sha256": digest(HERE / "inner-protocol.json"),
        "status": "pending",
        "modes": {mode: {"status": "pending"} for mode in MODES},
    }
    _write(output_dir / "run.json", state)
    full = None
    try:
        for mode in MODES:
            state["modes"][mode]["status"] = "running"
            _write(output_dir / "run.json", state)
            expected = (
                None if mode == MODES[0] else {c["source_id"]: c["search"] for c in full["cases"]}
            )
            with _mode(mode, expected) as module:
                result = module.run(HERE / "inner-protocol.json", output_dir / mode)
            _verify_written(output_dir / mode / "run.json", result)
            if mode == MODES[0]:
                full = _compatibility(output_dir / mode)
                state["historical_default_compatibility"] = "exact_except_new_protocol_hash"
            else:
                _same_evidence(full, result)
            state["modes"][mode] = {"status": "complete", "files": _inventory(output_dir / mode)}
            _write(output_dir / "run.json", state)
        verify()
        if set(p.name for p in output_dir.iterdir()) != {"run.json", *MODES} or any(
            _inventory(output_dir / mode) != state["modes"][mode]["files"] for mode in MODES
        ):
            raise ValueError("Mode outputs changed during execution")
        state["status"] = "complete"
        _write(output_dir / "run.json", state)
        _verify_written(output_dir / "run.json", state)
    except BaseException as error:
        state.update(status="aborted", error_type=type(error).__name__)
        _write(output_dir / "run.json", state)
        raise
    return state


def _verify_written(path, value):
    if path.read_bytes() != (json.dumps(value, indent=2, allow_nan=False) + "\n").encode():
        raise ValueError("Written assessment output changed")


def grade(protocol_path, run_dir, output_dir):
    verify = _freeze(protocol_path)
    run_dir, output_dir = Path(run_dir), Path(output_dir)
    raw = (run_dir / "run.json").read_bytes()
    state = json.loads(raw)

    def verify_run():
        verify()
        if (
            (run_dir / "run.json").read_bytes() != raw
            or state.get("version") != "compact-read-run-v1"
            or set(state["modes"]) != set(MODES)
            or state.get("historical_default_compatibility") != "exact_except_new_protocol_hash"
            or state["status"] != "complete"
            or state["protocol_sha256"] != digest(protocol_path)
            or state["inner_protocol_sha256"] != digest(HERE / "inner-protocol.json")
            or set(p.name for p in run_dir.iterdir()) != {"run.json", *MODES}
            or any(
                state["modes"][mode]["status"] != "complete"
                or _inventory(run_dir / mode) != state["modes"][mode]["files"]
                for mode in MODES
            )
        ):
            raise ValueError("Compact run is incomplete or changed")

    verify_run()
    full = _compatibility(run_dir / MODES[0])
    compact = json.loads((run_dir / MODES[1] / "run.json").read_bytes())
    _same_evidence(full, compact)
    if output_dir.resolve().is_relative_to(run_dir.resolve()):
        raise ValueError("Grade directory would change run inventory")
    output_dir.mkdir(exist_ok=False)
    result = {
        "version": "compact-read-grade-v1",
        "protocol_sha256": digest(protocol_path),
        "status": "pending",
        "conditions": {},
    }
    _write(output_dir / "summary.json", result)
    grades = {}
    try:
        for mode in MODES:
            expected = (
                None if mode == MODES[0] else {c["source_id"]: c["search"] for c in full["cases"]}
            )
            with _mode(mode, expected) as module:
                grade_result = module.grade(
                    HERE / "inner-protocol.json", run_dir / mode, output_dir / f"{mode}.json"
                )
            _verify_written(output_dir / f"{mode}.json", grade_result)
            grades[mode] = grade_result
            if mode == MODES[0]:
                historical = json.loads(HISTORICAL_GRADE.read_bytes())
                if (
                    grade_result["protocol_sha256"] != digest(HERE / "inner-protocol.json")
                    or grade_result["run_sha256"] != digest(run_dir / mode / "run.json")
                    or historical["protocol_sha256"] != digest(BASE / "comparison-protocol.json")
                    or historical["run_sha256"] != digest(HISTORY / "run.json")
                ):
                    raise ValueError("Historical grade attribution differs")
                normalized = copy.deepcopy(grade_result)
                for key in ["protocol_sha256", "run_sha256"]:
                    normalized[key] = historical[key]
                if canonical_hash(normalized) != canonical_hash(historical):
                    raise ValueError("Default grade differs from history")
            result["conditions"][mode] = {
                "grade_sha256": digest(output_dir / f"{mode}.json"),
                "selected_denominator": grade_result["selected_denominator"],
                "operations": grade_result["operations"],
                "priority_paired": grade_result["paired"],
                "policies": {
                    p: {
                        k: {field: value[field] for field in ["complete_count", "blocked_count"]}
                        for k, value in ks.items()
                    }
                    for p, ks in grade_result["conditions"].items()
                },
            }
            _write(output_dir / "summary.json", result)
        result["metadata_paired"] = {}
        for policy in grades[MODES[0]]["conditions"]:
            result["metadata_paired"][policy] = {}
            for key in ["top_1", "top_3", "top_5"]:
                pairs = list(
                    zip(
                        *(grades[mode]["conditions"][policy][key]["cases"] for mode in MODES),
                        strict=True,
                    )
                )
                result["metadata_paired"][policy][key] = {
                    "wins": sum(b["complete"] and not a["complete"] for a, b in pairs),
                    "losses": sum(a["complete"] and not b["complete"] for a, b in pairs),
                    "ties": sum(a["complete"] == b["complete"] for a, b in pairs),
                }
        verify_run()
        if set(p.name for p in output_dir.iterdir()) != {
            "summary.json",
            *(f"{mode}.json" for mode in MODES),
        }:
            raise ValueError("Grade output inventory changed")
        if any(
            digest(output_dir / f"{mode}.json") != result["conditions"][mode]["grade_sha256"]
            for mode in MODES
        ):
            raise ValueError("Grade outputs changed")
        result["status"] = "complete"
        _write(output_dir / "summary.json", result)
        _verify_written(output_dir / "summary.json", result)
    except BaseException as error:
        result.update(status="aborted", error_type=type(error).__name__)
        _write(output_dir / "summary.json", result)
        raise
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "grade"])
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    if args.action == "run":
        print(run(args.protocol, args.run_dir)["status"])
    else:
        if not args.output_dir:
            parser.error("grade requires --output-dir")
        print(grade(args.protocol, args.run_dir, args.output_dir)["status"])
