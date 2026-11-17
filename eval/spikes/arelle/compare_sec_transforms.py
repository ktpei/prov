"""Compare a fixed exposed issuer with and without the explicitly pinned plugin."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from sec_transforms import ROOT, sha, snapshot

HERE = Path(__file__).resolve().parent
EXPECTATIONS = HERE / "sec-transform-expectations.json"


def verify(control, candidate, expectations):
    expected = {fact["id"]: fact for fact in expectations["facts"]}
    if len(expected) != 12 or control["with_plugin"] or not candidate["with_plugin"]:
        raise ValueError("Unexpected comparison conditions")
    if not control["api_success"] or not candidate["api_success"] or candidate["model_errors"]:
        raise ValueError("Candidate validation failed")
    if control["diagnostic_counts"] != {
        "arelle:duplicateFacts": 78,
        "ix11.10.1.2:invalidTransformation": 4,
        "ix11.11.1.2:invalidTransformation": 8,
    }:
        raise ValueError("Original failure condition changed")
    if candidate["diagnostic_counts"] != {"arelle:duplicateFacts": 80}:
        raise ValueError("Unexpected candidate diagnostic")
    for key in (
        "runtime",
        "input_sha256",
        "loaded_document_sha256",
        "context_source_sha256",
        "unit_source_sha256",
    ):
        if control[key] != candidate[key]:
            raise ValueError(f"Paired source/runtime inputs differ: {key}")
    before = {fact["id"]: fact for fact in control["facts"]}
    after = {fact["id"]: fact for fact in candidate["facts"]}
    if len(before) != 504 or before.keys() != after.keys() or not expected.keys() <= before.keys():
        raise ValueError("Occurrence inventory changed")
    if {
        identifier for identifier, fact in before.items() if fact["validation_state"] < 4
    } != expected.keys():
        raise ValueError("Control invalid occurrence set differs")
    if any(fact["validation_state"] < 4 for fact in after.values()):
        raise ValueError("Candidate contains invalid facts")
    affected = {fact["id"]: fact for fact in candidate["affected_facts"]}
    if affected.keys() != expected.keys():
        raise ValueError("Affected occurrence inventory differs")
    for identifier, fact in before.items():
        if identifier not in expected:
            if fact != after[identifier]:
                raise ValueError("Unaffected occurrence changed")
        else:
            for key in (
                "id",
                "concept",
                "context_id",
                "unit_id",
                "nil",
                "original_occurrence_sha256",
            ):
                if fact[key] != after[identifier][key]:
                    raise ValueError("Affected occurrence provenance changed")
            target = affected[identifier]
            if (
                any(target[key] != value for key, value in after[identifier].items())
                or sha(target["typed_value"].encode()) != target["typed_value_sha256"]
            ):
                raise ValueError("Affected detail differs from occurrence fingerprint")
            for key in ("concept", "source_text", "format", "continued_at"):
                if target[key] != expected[identifier][key]:
                    raise ValueError("Source-derived expectation differs")
            if target["typed_value"] != expected[identifier]["expected_value"]:
                raise ValueError("Transformed value differs from independent expectation")
            kinds = {
                "boolean": {"bool"},
                "string": {"str"},
                "integer-valued numeric": {"int", "Decimal"},
            }
            if target["typed_value_type"] not in kinds[expected[identifier]["expected_kind"]]:
                raise ValueError("Unexpected transformed value kind")
    old_groups = {tuple(group["ids"]): group for group in control["duplicate_groups"]}
    new_groups = {tuple(group["ids"]): group for group in candidate["duplicate_groups"]}
    if not old_groups.keys() <= new_groups.keys() or any(
        new_groups[k] != v for k, v in old_groups.items()
    ):
        raise ValueError("Existing duplicate group changed")
    added = [new_groups[key] for key in new_groups.keys() - old_groups.keys()]
    expected_added = {
        tuple(
            sorted(
                identifier
                for identifier, fact in expected.items()
                if fact["concept"].endswith("}" + concept)
            )
        )
        for concept in ("NumberOfOperatingSegments", "NumberOfReportableSegments")
    }
    if {tuple(group["ids"]) for group in added} != expected_added or any(
        not group["complete"] or not group["consistent"] or group["inconsistent"] for group in added
    ):
        raise ValueError("Unexpected new duplicate groups")
    return {
        "unchanged_occurrences": 492,
        "verified_transformed_occurrences": 12,
        "all_schema_valid_occurrences": 504,
        "preserved_duplicate_groups": len(old_groups),
        "new_complete_duplicate_groups": sorted(added, key=lambda group: group["ids"]),
        "disposition": "targeted_transform_validation_passed; general_evidence_acceptance_unverified",
    }


def compare():
    captured = snapshot()
    input_hashes = {str(path.relative_to(ROOT)): sha(raw) for path, raw in captured.items()}
    captured[EXPECTATIONS] = EXPECTATIONS.read_bytes()
    captured[Path(__file__).resolve()] = Path(__file__).read_bytes()
    conditions = []
    with tempfile.TemporaryDirectory() as work:
        for mode in ("control", "candidate"):
            output = Path(work) / (mode + ".json")
            command = [sys.executable, str(HERE / "sec_transforms.py"), str(output)]
            if mode == "candidate":
                command.append("--with-plugin")
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=90)
            record = json.loads(output.read_text())
            if record["input_sha256"] != input_hashes:
                raise ValueError("Child input revision differs from parent")
            conditions.append(record)
    checks = verify(*conditions, json.loads(captured[EXPECTATIONS]))
    if any(path.read_bytes() != raw for path, raw in captured.items()):
        raise ValueError("Paired observation inputs changed")
    return {
        "version": "paired-sec-transform-verification-v1",
        "input_sha256": {str(path.relative_to(ROOT)): sha(raw) for path, raw in captured.items()},
        "checks": checks,
        "control": conditions[0],
        "candidate": conditions[1],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = compare()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
