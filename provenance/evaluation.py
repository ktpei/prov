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


def validate_report_evidence(task, report, *, directory=None):
    """Replay only read-only local tools to check trace consistency and quotes.

    This detects broken/inconsistent logs, not forged runs: logs are not signed.
    No model calls, expected answers, or external network requests are involved.
    """
    events = report.get("events")
    if not isinstance(events, list) or len(events) < 3:
        raise ValueError("Missing complete event trace")
    first, last = events[0], events[-1]
    sources = Sources(
        directory or Path(__file__).resolve().parent.parent / "data/corpus",
        retrieval_version=first.get("retrieval_version", "passage-v1"),
    )
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


def grade(task, report, *, directory=None):
    answer = report.get("answer") or {}
    expected = task["expected"]
    reasons, matched, used = [], [], set()
    try:
        validate_report_evidence(task, report, directory=directory)
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


def _patterns_present(text, patterns):
    """Anchor checks are deliberately lexical, never semantic entailment scores."""
    import re

    normalized = " ".join(text.split())
    return [bool(re.search(pattern, normalized, re.IGNORECASE)) for pattern in patterns]


def evaluate_packet(directory, benchmark_path, *, top_k=5, read_lines=40):
    """Run frozen retrieval probes without calling a model or using an answer key as input.

    Queries are a development retrieval suite, not autonomous question answering.
    Each expected evidence group requires all anchors within its source's retrieved
    windows. Full extraction coverage is measured independently from retrieval.
    """
    import time

    if type(top_k) is not int or not 1 <= top_k <= 5:
        raise ValueError("top_k must be between 1 and 5")
    if type(read_lines) is not int or not 1 <= read_lines <= 80:
        raise ValueError("read_lines must be between 1 and 80")
    sources = Sources(directory)
    benchmark = json.loads(Path(benchmark_path).read_text())
    expected_hashes = benchmark["source_hashes"]
    if (
        set(expected_hashes) != set(sources.documents)
        or not expected_hashes
        or any(
            source_id not in sources.documents
            or sources.documents[source_id]["sha256"] != expected_hash
            for source_id, expected_hash in expected_hashes.items()
        )
    ):
        raise ValueError("Benchmark source hashes differ from corpus; review and version anchors")
    tasks = benchmark["tasks"]
    if len({task["id"] for task in tasks}) != len(tasks):
        raise ValueError("Duplicate packet task IDs")
    rows = []
    started = time.perf_counter()
    for task in tasks:
        task_start = time.perf_counter()
        windows, text_by_source = {}, {}
        result_characters = 0
        for query in task["queries"]:
            # Only query text reaches the search tool, never reference answers or anchors.
            result = sources.search(query, 30)
            result_characters += len(json.dumps(result, ensure_ascii=False))
            for hit in result["results"][:top_k]:
                source_id = hit["id"]
                start = hit.get("start_line", 1)
                end = min(start + read_lines - 1, hit.get("end_line", start + read_lines - 1))
                key = (source_id, start, end)
                if key in windows:
                    continue
                read = sources.read(source_id, start, end, 30)
                text = "\n".join(line["text"] for line in read["lines"])
                windows[key] = {"source_id": source_id, "locator": read["locator"]}
                text_by_source.setdefault(source_id, []).append(text)
                result_characters += len(json.dumps(read, ensure_ascii=False))
        extraction, retrieval = [], []
        for group in task["evidence"]:
            source_id, patterns = group["source_id"], group["patterns"]
            if source_id not in expected_hashes:
                raise ValueError("Task evidence is not pinned to a source hash")
            if not patterns:
                raise ValueError("Expected evidence needs at least one anchor")
            extracted = _patterns_present(sources.documents[source_id]["text"], patterns)
            retrieved = _patterns_present("\n".join(text_by_source.get(source_id, [])), patterns)
            extraction.append(
                {"source_id": source_id, "anchors_found": extracted, "passed": all(extracted)}
            )
            retrieval.append(
                {"source_id": source_id, "anchors_found": retrieved, "passed": all(retrieved)}
            )
        rows.append(
            {
                "task_id": task["id"],
                "category": task["category"],
                "extraction": extraction,
                "retrieval": retrieval,
                "extraction_anchors_passed": all(group["passed"] for group in extraction)
                if extraction
                else None,
                "retrieval_anchors_passed": all(group["passed"] for group in retrieval)
                if retrieval
                else None,
                "evidence_windows": list(windows.values()),
                "tool_result_characters": result_characters,
                "latency_seconds": time.perf_counter() - task_start,
                "answer_quality": "not_measured_no_model_called",
                "abstention_quality": "requires_model_run_and_semantic_review"
                if not task["answerable"]
                else None,
            }
        )
    scored = [row for row in rows if row["extraction_anchors_passed"] is not None]
    return {
        "benchmark_version": benchmark["version"],
        "mode": "offline_fixed_query_retrieval",
        "source_hashes": expected_hashes,
        "settings": {
            "top_k": top_k,
            "read_lines": read_lines,
            "retrieval_version": sources.retrieval_version,
        },
        "summary": {
            "tasks": len(rows),
            "evidence_tasks": len(scored),
            "extraction_anchor_tasks_passed": sum(
                row["extraction_anchors_passed"] for row in scored
            ),
            "retrieval_anchor_tasks_passed": sum(row["retrieval_anchors_passed"] for row in scored),
            "latency_seconds": time.perf_counter() - started,
            "model_calls": 0,
            "api_cost_usd": 0,
            "model_tokens": None,
        },
        "tasks": rows,
        "limitations": [
            "Lexical anchor presence does not establish correct table structure or semantic support.",
            "Queries are authored retrieval probes, not model-selected searches or heldout evaluation.",
            "Absence and qualitative reasoning require model execution and human review.",
            "Tool-result characters measure returned content, not billed model context or tokens.",
        ],
    }


def grade_packet_answer(task, report, *, directory):
    """Pre-grade a real packet run; keep lexical, numerical, and human checks distinct."""
    sources = Sources(directory)
    allowed = task.get("source_ids", list(sources.documents))
    failures = []
    try:
        validate_report_evidence({**task, "source_ids": allowed}, report, directory=directory)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        failures.append(str(exc))
    if report.get("status") != "completed":
        failures.append("Run did not complete")
    if report.get("question") != task["question"]:
        failures.append("Run question does not match task")
    answer = report.get("answer")
    if not isinstance(answer, dict):
        answer = {}
    claims = answer.get("claims", [])
    if not isinstance(claims, list):
        claims = []
    claims = [claim for claim in claims if isinstance(claim, dict)]
    answerability = answer.get("answerable") is task["answerable"]
    numeric_checks = []
    for expected in task.get("numeric_claims", []):
        match = any(
            type(claim.get("value")) in (int, float)
            and math.isfinite(claim["value"])
            and abs(claim["value"] - expected["value"]) <= expected["tolerance"]
            and claim.get("unit") == expected["unit"]
            and claim.get("period") == expected["period"]
            for claim in claims
        )
        numeric_checks.append({"key": expected["key"], "passed": match})
    cited_text = {}
    for claim in claims:
        citations = claim.get("citations", [])
        if not isinstance(citations, list):
            continue
        for citation in citations:
            try:
                start, end = locator_range(citation["locator"])
                source_id = citation["source_id"]
                text = "\n".join(sources.documents[source_id]["text"].splitlines()[start - 1 : end])
                cited_text.setdefault(source_id, []).append(text)
            except (ValueError, TypeError, KeyError):
                continue  # Trace validation above reports malformed citations.
    coverage = [
        {
            "source_id": group["source_id"],
            "passed": all(
                _patterns_present(
                    "\n".join(cited_text.get(group["source_id"], [])), group["patterns"]
                )
            ),
        }
        for group in task["evidence"]
    ]
    return {
        "task_id": task["id"],
        "mode": report.get("mode"),
        "trace_and_quote_checks_passed": not failures,
        "trace_failures": failures,
        "answerability_passed": answerability,
        "numeric_claim_checks": numeric_checks,
        "citation_anchor_coverage": coverage,
        "mechanical_checks_passed": not failures
        and answerability
        and all(item["passed"] for item in numeric_checks + coverage),
        "semantic_answer_quality": "requires_human_review",
        "rubric": task["rubric"],
        "runtime_metrics": report.get("metrics"),
        "review": "Check metric labels, qualitative entailment, complete cross-source support, "
        "unsupported additions, and packet-scoped abstention. Mechanical pass is not task success.",
    }


def packet_main():
    """A separate command keeps v1's frozen benchmark and CLI behavior unchanged."""
    import argparse

    parser = argparse.ArgumentParser(description="Offline full-document retrieval benchmark")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--result", type=Path, help="Grade an existing model report instead")
    parser.add_argument("--task", help="Task ID required with --result")
    args = parser.parse_args()
    if args.result:
        if not args.task:
            parser.error("--result requires --task")
        tasks = json.loads(args.benchmark.read_text())["tasks"]
        task = next((task for task in tasks if task["id"] == args.task), None)
        if task is None:
            parser.error("Unknown packet task")
        report = grade_packet_answer(
            task, json.loads(args.result.read_text()), directory=args.corpus
        )
    else:
        report = evaluate_packet(args.corpus, args.benchmark)
    rendered = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    packet_main()
