"""Label-free, journaled reading of at most five frozen local search passages."""

import copy
import hashlib
import json
import os
from pathlib import Path

from provenance.sources import locator_range

POLICY = "ranked-parent-once-v1"


def _identity(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def _plan(sources, hits):
    if not isinstance(hits, list) or len(hits) > 5:
        raise ValueError("Expected at most five ordered hit projections")
    plan = []
    for hit in hits:
        if not isinstance(hit, dict) or set(hit) != {"source_id", "start_line", "end_line"}:
            raise ValueError("Reader accepts only source ID and parent bounds")
        sid, start, end = (hit[k] for k in ["source_id", "start_line", "end_line"])
        if not isinstance(sid, str) or sid not in sources.documents:
            raise ValueError("Unknown frozen source")
        source = sources.documents[sid]
        text = source.get("text")
        if not isinstance(text, str) or hashlib.sha256(text.encode()).hexdigest() != source.get(
            "sha256"
        ):
            raise ValueError("Reading requires hash-verified local text")
        if (
            type(start) is not int
            or type(end) is not int
            or not 1 <= start <= end <= len(text.splitlines())
            or end - start >= 80
        ):
            raise ValueError("Parent bounds must be within source and at most 80 lines")
        plan.append(dict(hit))
    return plan


def _validate_response(source, request, response):
    lines = response.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValueError("Read response has no lines")
    start, end = locator_range(response["locator"])
    text = source["text"].splitlines()
    if (
        response.get("id") != request["source_id"]
        or response.get("sha256") != source["sha256"]
        or response.get("original_sha256") != source.get("original_sha256")
        or response.get("total_lines") != len(text)
        or start != request["start_line"]
        or not start <= end <= request["end_line"]
        or len(lines) != end - start + 1
    ):
        raise ValueError("Read response identity or bounds mismatch")
    for number, line in zip(range(start, end + 1), lines, strict=True):
        if (
            type(line.get("line")) is not int
            or line["line"] != number
            or line.get("text") != text[number - 1]
        ):
            raise ValueError("Read response differs from exact source lines")
        if source.get("line_locations") and _identity(line.get("original_location")) != _identity(
            source["line_locations"][number - 1]
        ):
            raise ValueError("Read response original location mismatch")
    if sum(len(line["text"]) for line in lines) > 18000:
        raise ValueError("Read response exceeds text character budget")


def read_ranked_passages(sources, hits, journal_path):
    """Preserve rank slots and durable attempts; caller supplies replay-verified hits.

    No labels or questions are accepted. This is an offline baseline, not an agent
    policy or a model-context projection. A failed slot is never replaced.
    """
    plan = _plan(sources, hits)  # Validate every slot before any call or journal.
    snapshots = {h["source_id"]: copy.deepcopy(sources.documents[h["source_id"]]) for h in plan}
    records = []
    with Path(journal_path).open("x") as journal:

        def emit(event):
            journal.write(json.dumps(event, sort_keys=True, allow_nan=False) + "\n")
            journal.flush()
            os.fsync(journal.fileno())

        emit(
            {
                "event": "plan",
                "policy": POLICY,
                "hits": plan,
                "source_hashes": {sid: source["sha256"] for sid, source in snapshots.items()},
            }
        )
        for rank, request in enumerate(plan, 1):
            emit({"event": "started", "rank": rank, "request": request})
            record = {"rank": rank, "request": request}
            try:
                source = sources.documents[request["source_id"]]
                if _identity(source) != _identity(snapshots[request["source_id"]]):
                    raise RuntimeError("Source changed during reading")
                try:
                    response = sources.read(
                        request["source_id"], request["start_line"], request["end_line"], timeout=1
                    )
                except ValueError as error:
                    record.update(status="failed", error=str(error), response=None)
                else:
                    if _identity(source) != _identity(snapshots[request["source_id"]]):
                        raise RuntimeError("Source changed during reading")
                    response = copy.deepcopy(response)
                    _validate_response(source, request, response)
                    record.update(
                        status="returned",
                        response=response,
                        truncated=response["lines"][-1]["line"] < request["end_line"],
                    )
                if any(
                    _identity(sources.documents[sid]) != _identity(frozen)
                    for sid, frozen in snapshots.items()
                ):
                    raise RuntimeError("Source changed during reading")
            except BaseException as error:
                emit({"event": "aborted", "rank": rank, "error_type": type(error).__name__})
                raise
            records.append(record)
            emit({"event": "result", **record})
        budgets = {}
        for k in [1, 3, 5]:
            prefix = records[:k]
            returned = [r for r in prefix if r["status"] == "returned"]
            unique = {
                (r["request"]["source_id"], line["line"])
                for r in returned
                for line in r["response"]["lines"]
            }
            budgets[f"top_{k}"] = {
                "attempted_reads": len(prefix),
                "requested_lines": sum(
                    r["request"]["end_line"] - r["request"]["start_line"] + 1 for r in prefix
                ),
                "successful_reads": len(returned),
                "unique_returned_lines": len(unique),
                "returned_text_characters": sum(
                    len(line["text"]) for r in returned for line in r["response"]["lines"]
                ),
                "returned_json_bytes": sum(
                    len(
                        json.dumps(
                            r["response"], sort_keys=True, ensure_ascii=True, separators=(",", ":")
                        ).encode()
                    )
                    for r in returned
                ),
            }
        result = {"policy": POLICY, "records": records, "budgets": budgets}
        emit({"event": "complete", "budgets": budgets})
    return result
