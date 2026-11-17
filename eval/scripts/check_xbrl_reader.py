"""Inventory-wide reader reconstruction check, not execution of question cases."""

import argparse
import json
from collections import Counter
from pathlib import Path

from provenance.xbrl_occurrences import _source_nodes
from provenance.xbrl_reader import FactReader, canonical, sha

ROOT = Path(__file__).resolve().parents[2]
FACTS = ROOT / "eval/reports/xbrl-facts-2026-11-16/facts.json"
CORPUS = ROOT / "runs/native-html-v1-issuer-eligibility/old-dominion-2025-06-30-10q"


def verify_references(payload, fact, export, original_raw, original_locations=None):
    if original_locations is None:
        original_locations = {
            node["attributes"]["id"]: (node["start"], node["end"])
            for node in _source_nodes(original_raw)
            if node["attributes"].get("id")
        }
    by_id = {fragment["id"]: fragment for fragment in export["continuations"]}
    expected = [by_id[item["id"]] for item in fact["source_occurrence"]["continuation_fragments"]]
    if payload["continuations"] != expected:
        raise ValueError("Continuation records differ")
    inventory = [(fact["id"], "fact"), (fact["context_id"], "context")]
    if fact["unit_id"] is not None:
        inventory.append((fact["unit_id"], "unit"))
    inventory.extend((fragment["id"], "continuation") for fragment in expected)
    if [
        (fragment["id"], fragment["role"]) for fragment in payload["original_fragments"]
    ] != inventory:
        raise ValueError("Original fragment inventory differs")
    for fragment in payload["original_fragments"]:
        if (fragment["byte_start"], fragment["byte_end"]) != original_locations[fragment["id"]]:
            raise ValueError("Source fragment node interval differs")
        raw = original_raw[fragment["byte_start"] : fragment["byte_end"]]
        if raw != fragment["text"].encode() or sha(raw) != fragment["sha256"]:
            raise ValueError("Source fragment differs")


def build():
    paths = [FACTS, CORPUS / "sources.json", Path(__file__).resolve()]
    paths.extend(
        ROOT / "provenance" / name
        for name in (
            "xbrl_reader.py",
            "xbrl_occurrences.py",
            "table_structure.py",
            "source_availability.py",
        )
    )
    captured = {path: path.read_bytes() for path in paths}
    if (
        sha(captured[FACTS]) != "11462530f838361ad867201079ea6252f9c02703f9d4e20ec37a080220ee7986"
        or sha(captured[CORPUS / "sources.json"])
        != "1a63e3af4c9f2483ac3836a2c13d38a2d2eb8962eea66677d3a72ecbef5ae335"
    ):
        raise ValueError("Frozen export/source manifest differs")
    source = json.loads(captured[CORPUS / "sources.json"])["sources"][0]
    original = CORPUS / source["original_file"]
    captured[original] = original.read_bytes()
    source_raw = canonical(source).encode()
    reader = FactReader(
        captured[FACTS],
        source_raw,
        captured[original],
        export_sha256=sha(captured[FACTS]),
        source_sha256=sha(source_raw),
    )
    export = json.loads(captured[FACTS])
    original_locations = {
        node["attributes"]["id"]: (node["start"], node["end"])
        for node in _source_nodes(captured[original])
        if node["attributes"].get("id")
    }
    records = []
    for fact in export["facts"]:
        response = reader.read(fact["id"])
        record = {
            "id": fact["id"],
            "initial_status": response["status"],
            "payload_sha256": response["payload_sha256"],
            "payload_characters": response["payload_characters"],
            "response_hashes": [sha(canonical(response).encode())],
            "response_characters": [len(canonical(response))],
        }
        if response["status"] == "complete":
            payload = response["payload"]
            serialized = canonical(payload)
        else:
            chunks, start = [], response["next_start"]
            while start is not None:
                chunk = reader.read(fact["id"], start=start)
                if (
                    chunk["start"] != start
                    or chunk["chunk_sha256"] != sha(chunk["chunk"].encode())
                    or chunk["payload_sha256"] != response["payload_sha256"]
                ):
                    raise ValueError("Chunk identity mismatch")
                chunks.append(chunk["chunk"])
                record["response_hashes"].append(sha(canonical(chunk).encode()))
                record["response_characters"].append(len(canonical(chunk)))
                start = chunk["next_start"]
            serialized = "".join(chunks)
            payload = json.loads(serialized)
        if (
            len(serialized) != response["payload_characters"]
            or sha(serialized.encode()) != response["payload_sha256"]
            or payload["fact"] != fact
            or payload["context"] != export["contexts"][fact["context_id"]]
            or payload["unit"] != (export["units"][fact["unit_id"]] if fact["unit_id"] else None)
            or payload["duplicate_groups"]
            != [group for group in export["duplicate_groups"] if fact["id"] in group["occurrences"]]
        ):
            raise ValueError("Reconstruction changed exported evidence")
        verify_references(payload, fact, export, captured[original], original_locations)
        if max(record["response_characters"]) > 12_000:
            raise ValueError("Response limit exceeded")
        record["reconstruction_verified"] = True
        records.append(record)
    blocked = reader.read("unknown", as_of="2025-07-01T00:00:00Z")
    if blocked["status"] != "availability_blocked" or "payload" in blocked:
        raise ValueError("Historical availability bypass")
    if any(path.read_bytes() != raw for path, raw in captured.items()):
        raise ValueError("Check inputs changed")
    return {
        "version": "xbrl-reader-reconstruction-check-v1",
        "scope": "All exported occurrences; no question-case execution, discovery or financial grading.",
        "input_sha256": {str(path.relative_to(ROOT)): sha(raw) for path, raw in captured.items()},
        "summary": {
            "facts": len(records),
            "initial_status": dict(
                sorted(Counter(record["initial_status"] for record in records).items())
            ),
            "max_response_characters": max(
                max(record["response_characters"]) for record in records
            ),
            "responses": sum(len(record["response_hashes"]) for record in records),
            "availability_control": blocked["status"],
        },
        "records": records,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["summary"], indent=2))
