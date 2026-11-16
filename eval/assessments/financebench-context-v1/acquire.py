"""One-shot pinned PDF blob acquisition; no extraction or financial inspection."""

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from eval.scripts.acquire_native_html import NoRedirect, now
from eval.scripts.parent_read_assessment import _write
from eval.scripts.table_assessment_run import _load_object, _require_exact_keys, runtime_digest
from provenance.evidence_coverage import digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
METADATA = ROOT / "runs/financebench-context-v1-metadata"
MAX_BYTES = 32 * 1024 * 1024


def blob_sha(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def save(path, raw):
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def acquire(protocol_path, output):
    protocol_path, output = Path(protocol_path), Path(output)
    raw = protocol_path.read_bytes()
    protocol = _load_object(raw, "PDF acquisition protocol")
    _require_exact_keys(
        protocol,
        {
            "version",
            "script_sha256",
            "plan_sha256",
            "runtime_sha256",
            "selection_sha256",
            "inventory_sha256",
            "max_bytes",
            "socket_timeout_seconds",
            "elapsed_check_seconds",
        },
        "PDF acquisition protocol",
    )
    if (
        protocol["version"] != "financebench-pdf-acquisition-v1"
        or protocol["max_bytes"] != MAX_BYTES
        or protocol["socket_timeout_seconds"] != 20
        or protocol["elapsed_check_seconds"] != 120
    ):
        raise ValueError("Unsupported acquisition policy")
    selection = _load_object((HERE / "selection.json").read_bytes(), "Selection")
    inventory = _load_object((HERE / "inventory.json").read_bytes(), "Inventory")
    expected = {
        Path(__file__): protocol["script_sha256"],
        HERE / "acquisition-plan.md": protocol["plan_sha256"],
        HERE / "selection.json": protocol["selection_sha256"],
        HERE / "inventory.json": protocol["inventory_sha256"],
        METADATA / "commit.json": inventory["commit_response_sha256"],
        METADATA / "tree.json": inventory["tree_response_sha256"],
    }

    def verify():
        if (
            protocol_path.read_bytes() != raw
            or runtime_digest() != protocol["runtime_sha256"]
            or any(digest(p) != value for p, value in expected.items())
        ):
            raise ValueError("Acquisition frozen identity mismatch")

    verify()
    commit = _load_object((METADATA / "commit.json").read_bytes(), "Commit")
    tree = _load_object((METADATA / "tree.json").read_bytes(), "Tree")
    if (
        not re.fullmatch(r"[0-9a-f]{40}", inventory["revision"])
        or inventory["version"] != "financebench-context-pdf-inventory-v1"
        or selection["version"] != "financebench-context-selection-v1"
        or inventory["selection_sha256"] != protocol["selection_sha256"]
        or inventory["revision"] != selection["revision"]
        or commit["sha"] != inventory["revision"]
        or commit["tree"]["sha"] != tree["sha"]
        or tree["sha"] != inventory["tree_sha"]
        or tree["truncated"] is not False
    ):
        raise ValueError("Commit/tree/selection binding mismatch")
    sources = inventory["sources"]
    if (
        len(sources) != 6
        or len(selection["selected"]) != 6
        or len({s["doc_name"] for s in sources}) != 6
    ):
        raise ValueError("Expected six unique selected sources")
    for selected, source in zip(selection["selected"], sources, strict=True):
        name = source["doc_name"]
        entry = source["tree_entry"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError("Unsafe document name")
        url = f"https://raw.githubusercontent.com/patronus-ai/financebench/{inventory['revision']}/pdfs/{name}.pdf"
        matches = [row for row in tree["tree"] if row["path"] == f"pdfs/{name}.pdf"]
        if (
            selected["doc_name"] != name
            or selected["task_id"] != source["task_id"]
            or selected["doc_link"] != source["original_metadata_url"]
            or source["download_url"] != url
            or len(matches) != 1
            or matches[0] != entry
            or entry["mode"] != "100644"
            or entry["type"] != "blob"
            or type(entry["size"]) is not int
            or not 0 < entry["size"] <= MAX_BYTES
            or not re.fullmatch(r"[0-9a-f]{40}", entry["sha"])
        ):
            raise ValueError("Selected mirror identity mismatch")
    output.mkdir(exist_ok=False)
    result = {
        "version": "financebench-pdf-acquisition-result-v1",
        "protocol_sha256": digest(protocol_path),
        "status": "running",
        "selected_denominator": 6,
        "financial_content_inspected": False,
        "extraction_performed": False,
        "documents": [
            {
                "doc_name": s["doc_name"],
                "task_id": s["task_id"],
                "url": s["download_url"],
                "status": "pending",
            }
            for s in sources
        ],
    }
    _write(output / "acquisition.json", result)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        for source, item in zip(sources, result["documents"], strict=True):
            verify()
            body = bytearray()
            started = time.monotonic()
            item.update(status="request_started", requested_at=now())
            _write(output / "acquisition.json", result)
            try:
                request = urllib.request.Request(
                    item["url"],
                    headers={
                        "User-Agent": "ProvenanceXL-research/1",
                        "Accept-Encoding": "identity",
                    },
                )
                with opener.open(request, timeout=20) as response:
                    item.update(
                        http_status=response.status,
                        final_url=response.geturl(),
                        content_type=response.headers.get_content_type(),
                        content_encoding=response.headers.get("Content-Encoding", "identity"),
                        declared_content_length=response.headers.get("Content-Length"),
                    )
                    if (
                        response.status != 200
                        or response.geturl() != item["url"]
                        or item["content_type"]
                        not in {"application/pdf", "application/octet-stream"}
                        or item["content_encoding"].lower() != "identity"
                    ):
                        raise ValueError("Unexpected HTTP response")
                    cap = source["tree_entry"]["size"]
                    while len(body) <= cap:
                        if time.monotonic() - started > 120:
                            raise TimeoutError("Elapsed acquisition check exceeded")
                        chunk = response.read1(min(65536, cap + 1 - len(body)))
                        if not chunk:
                            item["eof_observed"] = True
                            break
                        body.extend(chunk)
                    if time.monotonic() - started > 120:
                        raise TimeoutError("Elapsed acquisition check exceeded")
                    if (
                        len(body) != cap
                        or not body.startswith(b"%PDF-")
                        or blob_sha(body) != source["tree_entry"]["sha"]
                    ):
                        raise ValueError("PDF prefix, byte length or pinned Git blob mismatch")
                    declared = item["declared_content_length"]
                    if declared is not None and int(declared) != len(body):
                        raise ValueError("Declared length mismatch")
                filename = item["doc_name"] + ".pdf"
                save(output / filename, body)
                item.update(
                    status="verified_blob",
                    file=filename,
                    bytes=len(body),
                    sha256=hashlib.sha256(body).hexdigest(),
                    git_blob_sha1=blob_sha(body),
                )
            except BaseException as error:
                item.update(
                    status="failed" if isinstance(error, Exception) else "interrupted",
                    error=f"{type(error).__name__}: {error}"[:1000],
                )
                if isinstance(error, urllib.error.HTTPError):
                    item["http_status"] = error.code
                    error.close()
                if body:
                    filename = item["doc_name"] + ".partial"
                    save(output / filename, body)
                    item.update(
                        partial_file=filename,
                        partial_bytes=len(body),
                        partial_sha256=hashlib.sha256(body).hexdigest(),
                    )
                if not isinstance(error, Exception):
                    raise
            finally:
                item.update(finished_at=now(), elapsed_seconds=time.monotonic() - started)
                _write(output / "acquisition.json", result)
        verify()
        for source, item in zip(sources, result["documents"], strict=True):
            if item["status"] == "verified_blob":
                body = (output / item["file"]).read_bytes()
                if (
                    digest(output / item["file"]) != item["sha256"]
                    or len(body) != source["tree_entry"]["size"]
                    or blob_sha(body) != source["tree_entry"]["sha"]
                ):
                    raise ValueError("Downloaded artifact changed")
        result.update(
            status="complete",
            completed_at=now(),
            verified_count=sum(d["status"] == "verified_blob" for d in result["documents"]),
        )
        _write(output / "acquisition.json", result)
    except BaseException as error:
        result.update(
            status="invalidated" if isinstance(error, Exception) else "interrupted",
            error_type=type(error).__name__,
        )
        _write(output / "acquisition.json", result)
        raise
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = acquire(args.protocol, args.output)
    print(json.dumps({"selected": 6, "verified": result["verified_count"]}))
