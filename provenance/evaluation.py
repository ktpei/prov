"""Dataset checks and a transparent mechanical pre-grader, not an LLM judge."""

import json
import math
from collections import Counter
from pathlib import Path

from provenance.model import validate_answer
from provenance.sources import Sources, locator_range


def load_tasks(path):
    return json.loads(path.read_text())["tasks"]


def validate_dataset(root):
    sources = Sources(root / "data/corpus")
    tasks = load_tasks(root / "eval/tasks.json")
    if len(tasks) != 25 or Counter(t["split"] for t in tasks) != {"dev": 10, "heldout": 15}:
        raise ValueError("Dataset must contain 10 dev and 15 heldout tasks")
    if len({t["id"] for t in tasks}) != 25:
        raise ValueError("Duplicate task IDs")
    if len({s["ticker"] for s in sources.documents.values()}) != 5:
        raise ValueError("Dataset must cover five companies")
    unanswerable = 0
    for task in tasks:
        if not task["question"].strip() or not task["rubric"].strip():
            raise ValueError("Each task needs a question and rubric")
        if task["category"] not in {"extraction", "guidance", "comparison", "unanswerable"}:
            raise ValueError("Invalid task category")
        expected = task["expected"]
        if type(expected["answerable"]) is not bool:
            raise ValueError("Expected answerable must be boolean")
        if bool(expected["claims"]) != expected["answerable"]:
            raise ValueError("Invalid expected claims for answerability")
        unanswerable += not expected["answerable"]
        if not task["source_ids"] or not set(task["source_ids"]) <= sources.documents.keys():
            raise ValueError("Unknown task source")
        keys = set()
        for claim in expected["claims"]:
            if claim["key"] in keys:
                raise ValueError("Duplicate expected key")
            keys.add(claim["key"])
            if not claim["unit"] or not claim["period"]:
                raise ValueError("Every expected claim needs units and period")
            if not math.isfinite(claim["tolerance"]) or claim["tolerance"] < 0:
                raise ValueError("Invalid tolerance")
            if type(claim["value"]) not in (int, float, str):
                raise ValueError("Invalid expected value")
            if isinstance(claim["value"], (int, float)) and not math.isfinite(claim["value"]):
                raise ValueError("Expected values must be finite")
            for citation in [claim, *claim.get("supporting_sources", [])]:
                source_id = citation["source_id"]
                if source_id not in task["source_ids"]:
                    raise ValueError("Claim cites source outside task scope")
                start, end = locator_range(citation["locator"])
                if end > len(sources.documents[source_id]["text"].splitlines()):
                    raise ValueError("Expected citation is outside document")
    if unanswerable < 3:
        raise ValueError("Include at least three unanswerable tasks")
    return {
        "tasks": len(tasks),
        "splits": dict(Counter(t["split"] for t in tasks)),
        "sources": len(sources.documents),
        "unanswerable": unanswerable,
        "categories": dict(Counter(t["category"] for t in tasks)),
        "checks": "Schemas, split counts, source hashes, and citation bounds; not semantic correctness",
    }


def mechanically_matches(actual, expected):
    value = actual.get("value")
    if isinstance(expected["value"], str):
        same_value = value == expected["value"]
    else:
        same_value = (
            type(value) in (int, float)
            and math.isfinite(value)
            and abs(value - expected["value"]) <= expected["tolerance"]
        )
    if not same_value or any(actual.get(k) != expected[k] for k in ("unit", "period")):
        return False
    for required in [expected, *expected.get("supporting_sources", [])]:
        a, b = locator_range(required["locator"])
        covered = False
        for citation in actual.get("citations", []):
            if citation.get("source_id") != required["source_id"]:
                continue
            try:
                c, d = locator_range(citation["locator"])
            except (ValueError, KeyError, TypeError):
                continue
            covered |= c <= b and a <= d
        if not covered:
            return False
    return True


def validate_report_evidence(task, report):
    """Replay only read-only local tools to check trace consistency and quotes.

    This detects broken/inconsistent logs, not forged runs: logs are not signed.
    No model calls, expected answers, or external network requests are involved.
    """
    sources = Sources(Path(__file__).resolve().parent.parent / "data/corpus")
    events = report.get("events")
    if not isinstance(events, list) or len(events) < 3:
        raise ValueError("Missing complete event trace")
    first, last = events[0], events[-1]
    if first.get("event") != "run_started" or last.get("event") != "run_finished":
        raise ValueError("Missing trace start or finish")
    if first.get("question") != task["question"] or first.get("mode") != report.get("mode"):
        raise ValueError("Trace question/mode mismatch")
    if first.get("source_mode") != "frozen_corpus" or last.get("status") != "completed":
        raise ValueError("Grading requires a completed frozen-corpus run")
    corpus = first["corpus"]
    if not corpus or any(
        key not in sources.documents or sources.documents[key]["sha256"] != value
        for key, value in corpus.items()
    ):
        raise ValueError("Trace corpus differs from current verified corpus")
    sources.documents = {key: sources.documents[key] for key in corpus}
    pending, final_response = {}, None
    for event in events:
        if event.get("event") == "tool_request":
            call = event["call"]
            if call["call_id"] in pending:
                raise ValueError("Duplicate pending call ID")
            pending[call["call_id"]] = call
        elif event.get("event") == "tool_result":
            call = pending.pop(event["call_id"], None)
            if call is None:
                raise ValueError("Tool result lacks matching request")
            try:
                args = json.loads(call.get("arguments", ""))
            except (json.JSONDecodeError, TypeError):
                actual = {"error": "Tool arguments must be valid JSON"}
            else:
                actual = sources.call(call.get("name"), args, 1)
            if actual != event["result"]:
                raise ValueError("Tool result differs from verified local evidence")
            if "lines" in actual and actual["id"] not in task["source_ids"]:
                raise ValueError("Read evidence outside task source scope")
        elif event.get("event") == "model_response":
            final_response = event["response"]
    if pending or final_response is None:
        raise ValueError("Incomplete tool/model trace")
    text = "".join(
        content.get("text", "")
        for item in final_response["output"]
        if item.get("type") == "message"
        for content in item.get("content", [])
        if content.get("type") == "output_text"
    )
    if json.loads(text) != report["answer"]:
        raise ValueError("Final answer differs from recorded model output")
    validate_answer(report["answer"], sources)
    if not sources.seen:
        raise ValueError("No evidence was read")


def grade(task, report):
    answer = report.get("answer") or {}
    expected = task["expected"]
    reasons, matched, used = [], [], set()
    try:
        validate_report_evidence(task, report)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        reasons.append(f"Invalid answer/evidence trace: {exc}")
        answer = {}  # Malformed answers must not reach the numerical pre-grader.
    if report.get("status") != "completed":
        reasons.append("Run did not complete")
    if report.get("question") != task["question"]:
        reasons.append("Run question does not match task")
    if answer.get("answerable") is not expected["answerable"]:
        reasons.append("Answerability mismatch")
    for claim in expected["claims"]:
        index = next(
            (
                i
                for i, actual in enumerate(answer.get("claims", []))
                if i not in used and mechanically_matches(actual, claim)
            ),
            None,
        )
        if index is None:
            reasons.append(f"Missing or mismatched claim: {claim['key']}")
        else:
            used.add(index)
            matched.append(claim["key"])
    return {
        "task_id": task["id"],
        "split": task["split"],
        "mode": report.get("mode"),
        "mechanical_checks_passed": not reasons,
        "matched_claims": matched,
        "failures": reasons,
        "requires_human_review": True,
        "review": "Verify metric identity, source entailment, derived arithmetic, extra claims, and abstention rationale. An offline replay is not model-quality evidence.",
    }
