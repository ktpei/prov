"""Fixed earlier-read-priority challenger; production context behavior is unchanged."""

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path

from eval.scripts.parent_read_assessment import _write
from eval.scripts.table_assessment_run import _load_object, _require_exact_keys, runtime_digest
from provenance.context import _omission, tool_result_chars
from provenance.context import project_messages as baseline_projector
from provenance.controls import LimitReached
from provenance.evidence_coverage import digest

POLICY = "earlier-optional-results-first-v1"
ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "eval/reports/context-retention-2026-11-16"
BASE_RESULT = ROOT / "runs/context-retention-2026-11-16.json"


def project_messages(messages, *, max_tool_result_chars=32000):
    """Keep required latest results, then try optional non-search results oldest-first."""
    if type(max_tool_result_chars) is not int or max_tool_result_chars < 1:
        raise ValueError("max_tool_result_chars must be a positive integer")
    calls = {m.get("call_id"): m.get("name") for m in messages if m.get("type") == "function_call"}
    outputs = [i for i, m in enumerate(messages) if m.get("type") == "function_call_output"]
    latest = {}
    for i in outputs:
        name = calls.get(messages[i].get("call_id"))
        if name in {"search", "read_source"}:
            latest[name] = i
    required = set(latest.values())
    projected = [dict(m) for m in messages]
    for i in outputs:
        if i not in required:
            projected[i] = _omission(messages[i])
    if tool_result_chars(projected) > max_tool_result_chars:
        raise LimitReached("tool_context_size_limit")
    # Sole policy difference from production: oldest rather than newest first.
    for i in outputs:
        if i in required or calls.get(messages[i].get("call_id")) == "search":
            continue
        previous = projected[i]
        projected[i] = dict(messages[i])
        if tool_result_chars(projected) > max_tool_result_chars:
            projected[i] = previous
    return projected


def _load_baseline():
    spec = importlib.util.spec_from_file_location("frozen_context_baseline", BASE / "analyze.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _challenger(module, outer_sha, output):
    original = module.project_messages
    if original is not baseline_projector:
        raise ValueError("Unexpected baseline projector reference")
    try:
        module.project_messages = project_messages
        result = module.execute(BASE / "protocol.json", output)
    finally:
        module.project_messages = original
    result["input_integrity_protocol_sha256"] = result.pop("protocol_sha256")
    result["experiment_protocol_sha256"] = outer_sha
    result["projector_policy"] = POLICY
    return result


def execute(protocol_path, output_dir):
    protocol_path, output_dir = Path(protocol_path), Path(output_dir)
    raw = protocol_path.read_bytes()
    protocol = _load_object(raw, "Priority protocol")
    _require_exact_keys(
        protocol,
        {
            "version",
            "policy",
            "limit",
            "analysis_sha256",
            "runtime_sha256",
            "baseline_protocol_sha256",
            "baseline_analysis_sha256",
            "baseline_result_sha256",
        },
        "Priority protocol",
    )
    if (
        protocol["version"] != "context-priority-protocol-v1"
        or protocol["policy"] != POLICY
        or protocol["limit"] != 32000
    ):
        raise ValueError("Unsupported priority protocol")

    def verify():
        if (
            protocol_path.read_bytes() != raw
            or digest(__file__) != protocol["analysis_sha256"]
            or runtime_digest() != protocol["runtime_sha256"]
            or digest(BASE / "analyze.py") != protocol["baseline_analysis_sha256"]
            or digest(BASE / "protocol.json") != protocol["baseline_protocol_sha256"]
            or digest(BASE_RESULT) != protocol["baseline_result_sha256"]
        ):
            raise ValueError("Priority frozen identity mismatch")

    verify()
    module = _load_baseline()
    output_dir.mkdir(exist_ok=False)
    state = {
        "version": "context-priority-run-v1",
        "protocol_sha256": digest(protocol_path),
        "status": "running_baseline",
    }
    _write(output_dir / "run.json", state)
    try:
        baseline = module.execute(BASE / "protocol.json", output_dir / "baseline.json")
        if digest(output_dir / "baseline.json") != protocol["baseline_result_sha256"]:
            raise ValueError("Historical context baseline does not replay exactly")
        state["status"] = "running_challenger"
        _write(output_dir / "run.json", state)
        with tempfile.TemporaryDirectory() as temporary:
            challenger = _challenger(module, digest(protocol_path), Path(temporary) / "result.json")
        _write(output_dir / "challenger.json", challenger)
        challenger_bytes = (json.dumps(challenger, indent=2, allow_nan=False) + "\n").encode()
        if [c["id"] for c in baseline["cases"]] != [c["id"] for c in challenger["cases"]]:
            raise ValueError("Condition case order differs")
        paired = {}
        for k in [1, 3, 5]:
            wins = losses = ties = 0
            for left, right in zip(baseline["cases"], challenger["cases"], strict=True):
                a = left["snapshots"][f"top_{k}"]["component_coverage"]["complete"]
                b = right["snapshots"][f"top_{k}"]["component_coverage"]["complete"]
                wins += b and not a
                losses += a and not b
                ties += a == b
            paired[f"top_{k}"] = {"wins": wins, "losses": losses, "ties": ties}
        verify()
        if (
            digest(output_dir / "baseline.json") != protocol["baseline_result_sha256"]
            or (output_dir / "challenger.json").read_bytes() != challenger_bytes
        ):
            raise ValueError("Condition output changed during comparison")
        state.update(
            status="complete",
            baseline_sha256=digest(output_dir / "baseline.json"),
            challenger_sha256=digest(output_dir / "challenger.json"),
            paired=paired,
        )
        _write(output_dir / "run.json", state)
    except BaseException as error:
        state.update(status="aborted", error_type=type(error).__name__)
        _write(output_dir / "run.json", state)
        raise
    return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.protocol, args.output)))
