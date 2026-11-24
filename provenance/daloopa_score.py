"""Deterministic numeric matching plus separately recorded, evidence-bound review."""

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from provenance.benchmarks import canonical_hash, decimal_answer
from provenance.daloopa import VERSION, load, model_input, unit, validate
from provenance.model import validate_answer
from provenance.sources import Sources

REVIEW_FIELDS = (
    "reference_verified",
    "metric_correct",
    "period_correct",
    "basis_correct",
    "original_source",
    "citation_support",
    "no_unsupported_additions",
)


def interval(passed, count):
    """95% Wilson interval; descriptive only for a fixed nonrandom benchmark subset."""
    if not count:
        return None
    z, p = 1.959963984540054, passed / count
    center = (p + z * z / (2 * count)) / (1 + z * z / count)
    half = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / (1 + z * z / count)
    return [max(0, center - half), min(1, center + half)]


def review_identity(task, record):
    return {
        "id": task["id"],
        "task_sha256": canonical_hash(task),
        "report_sha256": canonical_hash(record.get("report")),
        "evidence_sha256": canonical_hash(record.get("evidence")),
    }


def check_quotes(record):
    """Replay cited lines against captured documents; this is not semantic entailment."""
    report, evidence = record["report"], record["evidence"]
    events = report["events"]
    if (
        not events
        or events[0].get("event") != "run_started"
        or events[0].get("question") != report["question"]
        or events[-1].get("event") != "run_finished"
        or events[-1].get("status") != "completed"
    ):
        raise ValueError("Incomplete or mismatched event trace")
    pending, final_response = {}, None
    sources = Sources.__new__(Sources)
    sources.documents = evidence["documents"]
    sources.seen = defaultdict(set)
    for event in events:
        if event.get("event") == "model_response":
            final_response = event["response"]
        if event.get("event") == "tool_request":
            call = event["call"]
            if call["call_id"] in pending:
                raise ValueError("Duplicate tool call")
            pending[call["call_id"]] = call
        if event.get("event") != "tool_result":
            continue
        call = pending.pop(event["call_id"], None)
        if call is None:
            raise ValueError("Unmatched tool result")
        result = event["result"]
        if "lines" not in result:
            continue
        args = json.loads(call["arguments"])
        if call["name"] != "read_source" or args["source_id"] != result["id"]:
            raise ValueError("Read result/source mismatch")
        doc = sources.documents[result["id"]]
        if result["sha256"] != hashlib.sha256(doc["text"].encode()).hexdigest():
            raise ValueError("Evidence hash mismatch")
        lines = doc["text"].splitlines()
        for line in result["lines"]:
            if (
                type(line["line"]) is not int
                or not 1 <= line["line"] <= len(lines)
                or not args["start_line"] <= line["line"] <= args["end_line"]
            ):
                raise ValueError("Invalid evidence line")
            if lines[line["line"] - 1] != line["text"]:
                raise ValueError("Evidence differs from read trace")
            sources.seen[result["id"]].add(line["line"])
    if pending or final_response is None:
        raise ValueError("Incomplete model/tool trace")
    final_text = "".join(
        part.get("text", "")
        for item in final_response["output"]
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    )
    if json.loads(final_text) != report["answer"]:
        raise ValueError("Answer differs from final model response")
    validate_answer(report["answer"], sources)
    return bool(sources.seen)


def score_task(task, record, review=None):
    result = {
        "id": task["id"],
        "ticker": task["ticker"],
        "status": record.get("status", "not_started"),
        "reference_status": task["status"],
        "numeric_exact": False,
        "tolerance_1pct": False,
        "tolerance_5pct": False,
        "quote_valid": False,
        "supported_correct": None,
        "failure_category": None,
    }
    if task["status"] != "ready":
        result.update(
            numeric_exact=None,
            tolerance_1pct=None,
            tolerance_5pct=None,
            failure_category=task["status"],
        )
        return result
    if record.get("status") != "completed":
        result.update(supported_correct=False, failure_category="execution_incomplete")
        return result
    report = record.get("report", {})
    answer = report.get("answer") or {}
    if json.loads(report.get("question", "null")) != model_input(task):
        raise ValueError("Report question differs from safe task input")
    if report.get("status") != "completed":
        raise ValueError("Submission/report status mismatch")
    if answer.get("answerable") is False:
        result.update(supported_correct=False, failure_category="non_answer")
        return result
    claims = answer.get("claims", [])
    try:
        if len(claims) != 1 or claims[0]["key"] != "requested_answer":
            raise ValueError("Exactly one requested_answer claim required")
        claim = claims[0]
        value = decimal_answer(claim["value"])
        dimension, scale = unit(claim["unit"], strict=True)
        if dimension != task["reference"]["dimension"]:
            result["failure_category"] = "unit_dimension"
        else:
            expected = decimal_answer(task["reference"]["value"])
            difference = abs(value * scale - expected)
            result["numeric_exact"] = difference == 0
            # Zero has only exact-match success; never divide by zero or drop it silently.
            for tolerance in (1, 5):
                result[f"tolerance_{tolerance}pct"] = difference <= abs(expected) * tolerance / 100
            if difference:
                result["failure_category"] = "numeric_mismatch_requires_diagnosis"
        try:
            result["quote_valid"] = check_quotes(record)
        except (ValueError, KeyError, TypeError, IndexError):
            result["failure_category"] = result["failure_category"] or "invalid_citation"
    except (ValueError, KeyError, TypeError, IndexError):
        result["failure_category"] = "output_contract"
    if not result["numeric_exact"] or not result["quote_valid"]:
        result["supported_correct"] = False
    if review is not None:
        identity = review_identity(task, record)
        if any(review.get(key) != value for key, value in identity.items()):
            raise ValueError("Stale or mismatched semantic review")
        if review.get("reviewer_kind") not in {"human", "agent"} or not review.get("reviewer"):
            raise ValueError("Review requires explicit reviewer identity and kind")
        if any(type(review.get(key)) is not bool for key in REVIEW_FIELDS):
            raise ValueError("All semantic review decisions must be explicit booleans")
        if not isinstance(review.get("notes"), str) or not review["notes"].strip():
            raise ValueError("Review must explain source verification and decisions")
        result["reviewer_kind"] = review["reviewer_kind"]
        result["supported_correct"] = (
            result["numeric_exact"]
            and result["quote_valid"]
            and all(review[k] for k in REVIEW_FIELDS)
        )
        if not result["supported_correct"]:
            result["failure_category"] = result["failure_category"] or "semantic_review_failed"
    return result


def score(bundle, submission, reviews=()):
    validate(bundle)
    manifest = bundle["manifest"]
    if submission.get("prepared_sha256") != canonical_hash(manifest):
        raise ValueError("Submission belongs to a different prepared benchmark")
    profile = submission.get("profile")
    if profile not in {"quick", "full"}:
        raise ValueError("Unknown benchmark profile")
    selected = manifest[f"{profile}_ids"]
    rows = submission["records"]
    if [row["id"] for row in rows] != selected:
        raise ValueError("Submission must retain every selected case in frozen order")
    review_map = {review["id"]: review for review in reviews}
    if len(review_map) != len(reviews) or not set(review_map) <= set(selected):
        raise ValueError("Duplicate or unknown review IDs")
    tasks = {task["id"]: task for task in bundle["tasks"]}
    graded = [score_task(tasks[row["id"]], row, review_map.get(row["id"])) for row in rows]
    count = sum(row["numeric_exact"] is not None for row in graded)
    exact = sum(row["numeric_exact"] is True for row in graded)
    supported = sum(row["supported_correct"] is True for row in graded)
    pending = sum(row["supported_correct"] is None for row in graded)
    slices = {}
    for field in ("category", "difficulty", "currency"):
        buckets = defaultdict(list)
        for row in graded:
            buckets[tasks[row["id"]].get(field, "reserved")].append(row)
        slices[field] = {
            key: {
                "selected": len(values),
                "scorable": sum(v["numeric_exact"] is not None for v in values),
                "exact": sum(v["numeric_exact"] is True for v in values),
            }
            for key, values in sorted(buckets.items())
        }
    metrics = [r.get("report", {}).get("metrics", {}) for r in rows]
    return {
        "version": VERSION,
        "profile": profile,
        "prepared_sha256": canonical_hash(manifest),
        "submission_sha256": canonical_hash(submission),
        "reviews_sha256": canonical_hash(reviews),
        "full_inventory_count": len(tasks),
        "selected_count": len(selected),
        "scorable_count": count,
        "numeric_exact_count": exact,
        "numeric_match_accuracy": exact / count if count else None,
        "full_selection_numeric_accuracy": exact / len(selected)
        if count == len(selected)
        else None,
        "numeric_match_lower_bound_all_selected": exact / len(selected),
        "numeric_match_wilson_95": interval(exact, count),
        "interval_note": "Descriptive fixed-subset interval; not an unbiased estimate of the full population.",
        "tolerance_accuracy": {
            str(t): sum(r[f"tolerance_{t}pct"] is True for r in graded) / count if count else None
            for t in (1, 5)
        },
        "supported_correct_count": supported,
        "supported_pending_count": pending,
        "supported_accuracy": supported / len(selected) if not pending else None,
        "reviewer_kinds": dict(Counter(r["reviewer_kind"] for r in graded if "reviewer_kind" in r)),
        "statuses": dict(Counter(r["status"] for r in graded)),
        "failure_categories": dict(
            Counter(r["failure_category"] for r in graded if r["failure_category"])
        ),
        "accounted_cost_usd": submission.get("accounted_cost_usd", 0),
        "cost_uncertain": any(r.get("cost_uncertain", False) for r in rows),
        "model_calls": sum(m.get("model_calls", 0) for m in metrics),
        "task_latency_seconds": sum(m.get("latency_seconds", 0) for m in metrics),
        "slices": slices,
        "tasks": graded,
        "limitations": manifest["limitations"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = score(
        load(args.prepared),
        json.loads(args.submission.read_text()),
        json.loads(args.reviews.read_text()) if args.reviews else [],
    )
    with args.output.open("x") as handle:
        handle.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps({k: v for k, v in report.items() if k not in {"tasks", "slices", "limitations"}})
    )


if __name__ == "__main__":
    main()
