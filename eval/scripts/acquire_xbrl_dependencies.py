"""Acquire a bounded dependency graph from a previously receipted issuer schema."""

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

from provenance.xbrl_dependencies import LINK, XS, inspect_xml_references

ALLOWED_HOSTS = {"ir.odfl.com", "www.xbrl.org", "xbrl.sec.gov", "xbrl.fasb.org", "www.w3.org"}
MAX_DOCUMENTS = 64
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def acquire(seed_receipt, output, bundled_cache):
    seed_receipt, output, bundled_cache = map(Path, (seed_receipt, output, bundled_cache))
    receipt_raw = seed_receipt.read_bytes()
    seed = json.loads(receipt_raw)
    seed_path = (seed_receipt.parent / seed["local_file"]).resolve()
    if not seed_path.is_relative_to(seed_receipt.parent.resolve()):
        raise ValueError("Seed path escapes receipt directory")
    with seed_path.open("rb") as handle:
        seed_raw = handle.read(min(MAX_DOCUMENT_BYTES, MAX_TOTAL_BYTES) + 1)
    if len(seed_raw) > min(MAX_DOCUMENT_BYTES, MAX_TOTAL_BYTES):
        raise ValueError("Seed exceeds acquisition byte limits")
    if sha(seed_raw) != seed["response_sha256"] or seed["http_status"] != 200:
        raise ValueError("Seed receipt mismatch")
    output.mkdir(parents=True, exist_ok=False)
    (output / "documents").mkdir()
    code_paths = [Path(__file__), Path(inspect_xml_references.__code__.co_filename)]
    code_snapshot = {path: path.read_bytes() for path in code_paths}
    report = {
        "version": "bounded-xbrl-dependency-acquisition-v1",
        "seed_receipt_sha256": sha(receipt_raw),
        "driver_sha256": sha(code_snapshot[code_paths[0]]),
        "reference_parser_sha256": sha(code_snapshot[code_paths[1]]),
        "started_at": now(),
        "limits": {
            "documents": MAX_DOCUMENTS,
            "document_bytes": MAX_DOCUMENT_BYTES,
            "total_bytes": MAX_TOTAL_BYTES,
        },
        "redirects": "disabled",
        "retries": 0,
        "documents": [],
        "reference_edges": [],
        "status": "running",
    }
    queue = [(seed["canonical_url"], seed["final_url"])]
    scheduled = {seed["canonical_url"]: seed["final_url"]}
    opener = urllib.request.build_opener(NoRedirect())
    total = 0

    def persist():
        temporary = output / ".receipt.tmp"
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(output / "receipt.json")

    persist()
    for canonical, delivery in queue:
        record = {"canonical_url": canonical, "delivery_url": delivery, "started_at": now()}
        report["documents"].append(record)
        try:
            if total >= MAX_TOTAL_BYTES:
                raise ValueError("Body-byte acquisition budget exhausted")
            parsed = urlsplit(delivery)
            if (
                parsed.hostname not in ALLOWED_HOSTS
                or parsed.query
                or parsed.port not in {None, 80, 443}
            ):
                raise ValueError("Delivery location outside acquisition policy")
            if parsed.hostname == "ir.odfl.com" and not parsed.path.startswith(
                "/sec-filings/all-sec-filings/content/0000950170-25-103916/"
            ):
                raise ValueError("Issuer dependency outside selected accession")
            cached = (
                bundled_cache / parsed.scheme / parsed.netloc / parsed.path.lstrip("/")
            ).resolve()
            if not cached.is_relative_to(bundled_cache.resolve()):
                raise ValueError("Cache path escape")
            if canonical == seed["canonical_url"]:
                raw = seed_raw
                record.update(origin="receipted_seed", response_sha256=sha(raw))
            elif cached.is_file():
                with cached.open("rb") as handle:
                    raw = handle.read(min(MAX_DOCUMENT_BYTES, MAX_TOTAL_BYTES - total) + 1)
                record.update(
                    origin="explicit_bundled_cache",
                    cached_file=str(cached),
                    response_sha256=sha(raw),
                )
            else:
                time.sleep(0.2)
                with opener.open(
                    urllib.request.Request(
                        delivery,
                        headers={
                            "User-Agent": "ProvenanceXL-research/1 (https://github.com/ktpei/prov; noncommercial assessment)",
                            "Accept-Encoding": "identity",
                        },
                    ),
                    timeout=30,
                ) as response:
                    raw = response.read(min(MAX_DOCUMENT_BYTES, MAX_TOTAL_BYTES - total) + 1)
                    record.update(
                        origin="network",
                        http_status=response.status,
                        final_url=response.geturl(),
                        content_type=response.headers.get("Content-Type"),
                        response_sha256=sha(raw),
                    )
            total += len(raw)
            if len(raw) > MAX_DOCUMENT_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError("Byte limit exceeded (one overflow-detection byte permitted)")
            local = "documents/" + sha(raw) + ".xml"
            path = output / local
            if not path.exists():
                path.write_bytes(raw)
            record.update(local_file=local, response_bytes=len(raw))
            inventory = inspect_xml_references(raw, canonical_url=canonical, delivery_url=delivery)
            if inventory["root_name"] not in {f"{{{XS}}}schema", f"{{{LINK}}}linkbase"}:
                raise ValueError("Dependency is neither XML schema nor linkbase")
            record.update(
                status="xml_reference_inventory",
                root_name=inventory["root_name"],
                target_namespace=inventory["target_namespace"],
            )
            for edge in inventory["references"]:
                edge = {"parent_url": canonical, "parent_sha256": sha(raw), **edge}
                report["reference_edges"].append(edge)
                if edge["status"] != "declared_reference":
                    continue
                target, route = edge["canonical_url"], edge["delivery_url"]
                if target in scheduled:
                    if scheduled[target] != route:
                        edge["status"] = "conflicting_delivery_route"
                elif len(queue) >= MAX_DOCUMENTS:
                    edge["status"] = "document_limit"
                else:
                    scheduled[target] = route
                    queue.append((target, route))
        except (OSError, ValueError, ElementTree.ParseError, urllib.error.URLError) as error:
            record.update(status="failed", error=f"{type(error).__name__}: {error}")
            if isinstance(error, urllib.error.HTTPError):
                record["http_status"] = error.code
        record["finished_at"] = now()
        persist()
    documents = {record["canonical_url"]: record for record in report["documents"]}
    for edge in report["reference_edges"]:
        target = documents.get(edge.get("canonical_url"))
        if edge["status"] == "declared_reference":
            if not target or target["status"] != "xml_reference_inventory":
                edge["status"] = "unavailable_dependency"
            elif (
                edge["kind"] == "import"
                and edge.get("expected_namespace") != target["target_namespace"]
            ):
                edge["status"] = "namespace_mismatch"
    report.update(
        status="reference_graph_acquired"
        if all(record["status"] == "xml_reference_inventory" for record in report["documents"])
        and all(edge["status"] == "declared_reference" for edge in report["reference_edges"])
        else "incomplete_dependency_graph",
        finished_at=now(),
        observed_body_bytes=total,
        claim="Acquisition/reference graph only; Arelle DTS validation and financial facts unverified",
    )
    invalidation = None
    with seed_path.open("rb") as handle:
        seed_after = handle.read(len(seed_raw) + 1)
    if seed_receipt.read_bytes() != receipt_raw or seed_after != seed_raw:
        invalidation = "Seed changed during acquisition"
    if any(path.read_bytes() != raw for path, raw in code_snapshot.items()):
        invalidation = "Driver or parser changed during acquisition"
    if invalidation:
        report.update(status="invalidated", error=invalidation)
        persist()
        raise ValueError(invalidation)
    persist()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seed_receipt", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("bundled_cache", type=Path)
    args = parser.parse_args()
    result = acquire(args.seed_receipt, args.output, args.bundled_cache)
    print(
        json.dumps(
            {
                "status": result["status"],
                "documents": len(result["documents"]),
                "edges": len(result["reference_edges"]),
            }
        )
    )
