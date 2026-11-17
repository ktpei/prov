"""Record deterministic synthetic boundary scenarios using the acceptance fixtures."""

import argparse
import hashlib
import json
from pathlib import Path

from test_guarded_values import GuardedValueAcceptance
from typed_values import HERE


def record():
    code = [Path(__file__).resolve()] + [
        HERE / name
        for name in (
            "typed_values.py",
            "typed_values_guarded.py",
            "test_typed_values.py",
            "test_guarded_values.py",
            "valid-values.xhtml",
            "synthetic.xsd",
            "typed-manifest.json",
        )
    ]
    snapshots = {p: p.read_bytes() for p in code}
    baseline = json.loads(snapshots[HERE / "typed-manifest.json"])
    for name in ("valid-values.xhtml", "synthetic.xsd"):
        if hashlib.sha256(snapshots[HERE / name]).hexdigest() != baseline[name]:
            raise ValueError("Base synthetic fixture differs from frozen manifest")
    cases = []
    scenarios = [
        "baseline",
        "negative_scale",
        "explicit_utc",
        "positive_fractional",
        "negative_fractional",
        "negative_zero_fractional",
        "nonnillable_nil",
        "complete_duplicates",
        "incomplete_consistent_duplicates",
        "inconsistent_duplicates",
    ]
    for name in scenarios:
        fixture = GuardedValueAcceptance()
        fixture.setUp()
        try:
            if name == "negative_scale":
                fixture.source.write_text(
                    fixture.source.read_text().replace('scale="3"', 'scale="-2"')
                )
            elif name in {
                "explicit_utc",
                "positive_fractional",
                "negative_fractional",
                "negative_zero_fractional",
            }:
                fixture.dates(
                    {
                        "explicit_utc": "Z",
                        "positive_fractional": "+05:30",
                        "negative_fractional": "-05:30",
                        "negative_zero_fractional": "-00:30",
                    }[name]
                )
            elif name == "nonnillable_nil":
                from lxml import etree

                tree = etree.parse(str(fixture.schema))
                tree.xpath('//*[@name="MissingAmount"]')[0].set("nillable", "false")
                tree.write(str(fixture.schema), encoding="utf-8")
            elif name == "complete_duplicates":
                fixture.duplicate("assets")
            elif name == "incomplete_consistent_duplicates":
                fixture.duplicate("eps", text="2.5", decimals="1")
            elif name == "inconsistent_duplicates":
                fixture.duplicate("assets", text="13")
            child, result = fixture.raw()
            candidate_manifest = json.loads(fixture.manifest.read_text())
            if any(
                candidate_manifest[key] != value
                for key, value in baseline.items()
                if key.startswith("http://")
            ):
                raise ValueError("Bundled standard schema differs from frozen baseline")
            rejected = name in {
                "negative_fractional",
                "negative_zero_fractional",
                "nonnillable_nil",
            }
            if (child.returncode != 0) != rejected:
                raise ValueError(f"Unexpected scenario disposition: {name}: {child.stderr}")
            rejection = child.stderr.strip().splitlines()[-1] if rejected else None
            if rejected:
                marker = (
                    "nilNonNillableElement"
                    if name == "nonnillable_nil"
                    else "Library normalized period disagrees"
                )
                if marker not in rejection:
                    raise ValueError("Unexpected rejection cause")
                accepted = 0
            else:
                expected_count = 6 if "duplicates" in name else 5
                if len(result["facts"]) != expected_count:
                    raise ValueError("Occurrence inventory differs")
                accepted = sum(
                    f["acceptance"] == "schema_valid_occurrence" for f in result["facts"]
                )
                if accepted != (4 if name == "inconsistent_duplicates" else expected_count):
                    raise ValueError("Unexpected accepted occurrence count")
            cases.append(
                {
                    "scenario": name,
                    "candidate_input_sha256": candidate_manifest,
                    "disposition": "rejected"
                    if rejected
                    else "exported_with_per_occurrence_status",
                    "accepted_schema_occurrences": accepted,
                    "rejection": rejection,
                    "result": result,
                }
            )
        finally:
            fixture.doCleanups()
    if any(path.read_bytes() != raw for path, raw in snapshots.items()):
        raise ValueError("Matrix code or base fixture changed")
    return {
        "version": "guarded-synthetic-boundary-matrix-v1",
        "inputs": {p.name: hashlib.sha256(raw).hexdigest() for p, raw in snapshots.items()},
        "cases": cases,
        "limitations": [
            "Synthetic numeric fixtures only; no issuer or financial answer evaluation.",
            "Exported schema-valid occurrences are not claims of financial correctness.",
            "Negative fractional timezone cases are rejected, not repaired or supported.",
            "Full validation messages and arbitrary runtime resources are not serialized.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = record()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
