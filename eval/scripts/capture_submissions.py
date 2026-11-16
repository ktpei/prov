"""Capture frozen SEC submission containers; never qualify them as filing evidence."""

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from eval.scripts.acquire_native_html import USER_AGENT, NoRedirect, now, persist
from eval.scripts.table_assessment_run import _load_object, runtime_digest

MAX_BYTES = 32 * 1024 * 1024
ELAPSED_LIMIT_SECONDS = 120


def capture(selection_path, candidates_path, selection_hash, candidates_hash, output):
    inputs = []
    for path, expected in [(selection_path, selection_hash), (candidates_path, candidates_hash)]:
        raw = Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("Frozen input hash mismatch")
        inputs.append(_load_object(raw, "Acquisition input"))
    selection, candidates = inputs
    documents = selection["documents"]
    ids = [d["source_id"] for d in documents]
    if len(ids) != 6 or len(set(ids)) != 6:
        raise ValueError("Expected six unique selected documents")
    if candidates.get("selection_sha256") != selection_hash:
        raise ValueError("Candidates change selected cohort")
    routes = {}
    for candidate in candidates["sources"]:
        source_id = candidate["source_id"]
        if source_id not in ids or source_id in routes:
            raise ValueError("Unknown or duplicate candidate")
        document = documents[ids.index(source_id)]
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", source_id):
            raise ValueError("Unsafe source ID")
        accession = document["accession"]
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
            raise ValueError("Invalid accession")
        expected_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(document['cik'])}/"
            f"{accession.replace('-', '')}/{accession}.txt"
        )
        if candidate["complete_submission_url"] != expected_url or any(
            candidate[key] != document[key]
            for key in ["accession", "cik", "period_end", "index_url"]
        ):
            raise ValueError("Submission route does not match selected identity")
        if (
            candidate["expected_document_type"] != document["form"]
            or candidate["expected_filename"] != document["primary_url"].rsplit("/", 1)[1]
            or type(candidate["expected_sequence"]) is not int
            or candidate["expected_sequence"] != 1
        ):
            raise ValueError("Primary member metadata mismatch")
        routes[source_id] = expected_url
    if len(routes) != 4:
        raise ValueError("Expected four frozen submission candidates")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "version": "sec-submission-capture-v1",
        "selection_sha256": selection_hash,
        "candidates_sha256": candidates_hash,
        "runtime_sha256": runtime_digest(),
        "capture_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "artifact_class": "unverified_submission_container",
        "request_policy": "One request per candidate; no redirects/retries; one second between requests; 20-second socket-operation timeout; identity encoding",
        "user_agent": USER_AGENT,
        "max_response_bytes": MAX_BYTES,
        "elapsed_limit_seconds": ELAPSED_LIMIT_SECONDS,
        "elapsed_limit_note": "Checked between response reads; urllib header/chunk parsing may perform multiple socket operations. No hard total-duration bound.",
        "selected_denominator": 6,
        "candidate_denominator": 4,
        "identity_verified_count": 0,
        "primary_extracted": False,
        "corpus_eligible": False,
        "model_calls": 0,
        "documents": [
            {
                "source_id": sid,
                "url": routes.get(sid),
                "status": "pending" if sid in routes else "not_requested_no_candidate",
            }
            for sid in ids
        ],
    }
    persist(report, output)
    opener = urllib.request.build_opener(NoRedirect)
    attempts = 0
    for entry in report["documents"]:
        if entry["url"] is None:
            continue
        body = bytearray()
        started = time.monotonic()
        try:
            if attempts:
                time.sleep(1)
            entry.update(status="request_started", requested_at=now())
            started = time.monotonic()
            persist(report, output)
            attempts += 1
            request = urllib.request.Request(
                entry["url"], headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
            )
            with opener.open(request, timeout=20) as response:
                entry.update(
                    http_status=response.status,
                    final_url=response.geturl(),
                    content_type=response.headers.get_content_type(),
                    declared_content_length=response.headers.get("Content-Length"),
                    content_encoding=response.headers.get("Content-Encoding", "identity"),
                )
                if (
                    response.status != 200
                    or response.geturl() != entry["url"]
                    or entry["content_type"] not in {"text/plain", "application/octet-stream"}
                    or entry["content_encoding"].lower() != "identity"
                ):
                    raise ValueError("Unexpected HTTP status, URL, media type or encoding")
                while len(body) <= MAX_BYTES:
                    if time.monotonic() - started > ELAPSED_LIMIT_SECONDS:
                        raise TimeoutError("Container elapsed-time limit exceeded")
                    chunk = response.read1(min(65536, MAX_BYTES + 1 - len(body)))
                    if not chunk:
                        entry["eof_observed"] = True
                        break
                    body.extend(chunk)
                if time.monotonic() - started > ELAPSED_LIMIT_SECONDS:
                    raise TimeoutError("Container elapsed-time limit exceeded")
                if len(body) > MAX_BYTES:
                    raise ValueError("Container exceeds byte limit")
                length = entry["declared_content_length"]
                if length is not None and int(length) != len(body):
                    raise ValueError("Declared length mismatch")
                if not body:
                    raise ValueError("Empty response")
            filename = entry["source_id"] + ".unverified.txt"
            (output / filename).write_bytes(body)
            entry.update(
                status="captured_unverified",
                container_file=filename,
                response_bytes=len(body),
                response_sha256=hashlib.sha256(body).hexdigest(),
                observed_at=now(),
            )
        except BaseException as exc:
            entry.update(
                status="failed" if isinstance(exc, Exception) else "interrupted",
                error=f"{type(exc).__name__}: {exc}"[:1000],
            )
            if isinstance(exc, urllib.error.HTTPError):
                entry["http_status"] = exc.code
            if body:
                filename = entry["source_id"] + ".partial"
                (output / filename).write_bytes(body)
                entry.update(
                    partial_file=filename,
                    partial_bytes=len(body),
                    partial_sha256=hashlib.sha256(body).hexdigest(),
                )
            entry["finished_at"] = now()
            entry["elapsed_seconds"] = time.monotonic() - started
            persist(report, output)
            if not isinstance(exc, Exception):
                raise
        else:
            entry["finished_at"] = now()
            entry["elapsed_seconds"] = time.monotonic() - started
            persist(report, output)
    report.update(
        completed_at=now(),
        captured_unverified_count=sum(
            e["status"] == "captured_unverified" for e in report["documents"]
        ),
    )
    persist(report, output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["selection", "candidates", "selection-hash", "candidates-hash", "output"]:
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    report = capture(
        args.selection, args.candidates, args.selection_hash, args.candidates_hash, args.output
    )
    print(
        json.dumps(
            {
                "selected": 6,
                "candidates": 4,
                "captured_unverified": report["captured_unverified_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
