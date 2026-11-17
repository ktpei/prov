"""Bind one exposed filing's source occurrence locations to its frozen runtime observation."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from provenance.xbrl_occurrences import occurrence_sidecar

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "runs/native-html-v1-issuer-acquisition/old-dominion-2025-06-30-10q.html"
TABLES = ROOT / "runs/native-html-v1-issuer-eligibility/old-dominion-2025-06-30-10q-tables.json"
OBSERVATION = ROOT / "eval/spikes/arelle/sec-transform-result.json"
URI = "https://www.sec.gov/Archives/edgar/data/878927/000095017025103916/odfl-20250630.htm"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build():
    from lxml import etree

    paths = [
        ORIGINAL,
        TABLES,
        OBSERVATION,
        Path(__file__).resolve(),
        ROOT / "provenance/xbrl_occurrences.py",
        ROOT / "provenance/table_structure.py",
    ]
    captured = {path: path.read_bytes() for path in paths}
    if (
        sha(captured[OBSERVATION])
        != "6e68cad69b919b0f700f27d8f6fc7a2a416018ef900e55c0f0b01a7747ab2230"
    ):
        raise ValueError("Frozen runtime observation differs")
    result = occurrence_sidecar(captured[ORIGINAL], captured[TABLES])
    candidate = json.loads(captured[OBSERVATION])["candidate"]
    if candidate["loaded_document_sha256"].get(URI) != result["original_sha256"]:
        raise ValueError("Runtime original hash differs")
    parsed = etree.fromstring(
        captured[ORIGINAL],
        etree.XMLParser(recover=False, no_network=True, resolve_entities=False, load_dtd=False),
    )
    source_by_id = {element.get("id"): element for element in parsed.iter() if element.get("id")}
    runtime = {fact["id"]: fact for fact in candidate["facts"]}
    if runtime.keys() != {fact["id"] for fact in result["facts"]}:
        raise ValueError("Source/runtime occurrence inventory differs")
    for fact in result["facts"]:
        recorded = runtime[fact["id"]]
        source = source_by_id[fact["id"]]
        if (
            sha(etree.tostring(source, method="c14n")) != recorded["original_occurrence_sha256"]
            or fact["expanded_concept"] != recorded["concept"]
            or fact["context_ref"] != recorded["context_id"]
            or fact["unit_ref"] != recorded["unit_id"]
            or recorded["validation_state"] < 4
        ):
            raise ValueError("Source/runtime occurrence binding differs")
        fact["runtime_schema_validation_state"] = recorded["validation_state"]
        fact["runtime_source_identity_match"] = True
    result["runtime_observation_sha256"] = sha(captured[OBSERVATION])
    result["canonical_url"] = URI
    result["input_sha256"] = {
        str(path.relative_to(ROOT)): sha(raw) for path, raw in captured.items()
    }
    result["summary"] = {
        "facts": len(result["facts"]),
        "continuations": len(result["continuations"]),
        "dispositions": dict(
            sorted(Counter(fact["source_disposition"] for fact in result["facts"]).items())
        ),
        "distinct_mapped_cells": len(
            {fact["table_mapping"]["cell_id"] for fact in result["facts"] if fact["table_mapping"]}
        ),
        "facts_with_fact_ancestors": sum(
            bool(fact["ancestor_fact_ids"]) for fact in result["facts"]
        ),
        "facts_inside_continuation_subtrees": sum(
            bool(fact["ancestor_continuation_ids"]) for fact in result["facts"]
        ),
        "continuation_issues": sum(
            len(fragment["continuation_issues"]) for fragment in result["continuations"]
        ),
    }
    if result["summary"] != {
        "facts": 504,
        "continuations": 6,
        "dispositions": {"cell_mapped": 420, "explicitly_hidden": 7, "outside_table": 77},
        "distinct_mapped_cells": 412,
        "facts_with_fact_ancestors": 136,
        "facts_inside_continuation_subtrees": 95,
        "continuation_issues": 0,
    }:
        raise ValueError("Independent source inventory expectations differ")
    if any(path.read_bytes() != raw for path, raw in captured.items()):
        raise ValueError("Report inputs changed")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"]))
