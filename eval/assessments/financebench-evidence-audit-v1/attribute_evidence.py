"""Attribute locked judgments to saved read evidence; never retrieve or judge."""

import hashlib
import importlib.util
import json
from pathlib import Path

from eval.scripts.table_assessment_run import _load_object
from provenance.evidence_coverage import digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT / "runs/financebench-page-ranking-v1"
POLICIES = ("production-newest-first", "earlier-optional-results-first-v1")
LOCK_SHA = "6c5cfeae65d5a34ed70daba951eb751f992e04c5ce100d23f45146d0dff9eebf"


def input_paths():
    local = [
        "attribute_evidence.py",
        "attribution-plan.md",
        "validate_evidence_review.py",
        "prepare_evidence.py",
        "evidence-review-instructions.md",
        "stage-1/custodian.json",
        "stage-2/receipt.json",
        "reviews/stage-2-lock.json",
        "reviews/evidence-adjudicated.json",
        "reviews/evidence-adjudication-notes.json",
        "reviews/evidence-adjudicated-validation.json",
        "reviews/evidence-adjudication-notes-validation.json",
    ]
    local += [f"stage-2/reviewer/Q{n:02d}.json" for n in range(1, 7)]
    paths = [HERE / n for n in local] + [
        ROOT / "tests/test_evidence_attribution.py",
        RUN / "deterministic/run.json",
        ROOT / "runs/financebench-page-ranking-v1-grade.json",
    ]
    return {str(p.relative_to(ROOT)): p for p in paths}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cited_lines(citations):
    return {
        (s["source_id"], n) for s in citations for n in range(s["start_line"], s["end_line"] + 1)
    }


def assess_interpretation(interpretation, available):
    sets = []
    for evidence in interpretation["complete_evidence_sets"]:
        missing = {
            role: [list(pair) for pair in sorted(cited_lines(spans) - available)]
            for role, spans in evidence["requirements"].items()
        }
        sets.append(
            {"id": evidence["id"], "covered": not any(missing.values()), "missing_lines": missing}
        )
    return {
        "interpretation_id": interpretation["interpretation_id"],
        "disposition": "adjudicated_sets" if sets else "no_adjudicated_complete_set",
        "unresolved_requirements": {
            r["requirement_id"]: r["status"]
            for r in interpretation["requirements"]
            if r["status"] != "supported"
        },
        "any_set_covered": any(s["covered"] for s in sets),
        "sets": sets,
    }


def retained_lines(records, condition):
    """Read hits retain requested bounds even when omitted; use returned bytes."""
    ranks = condition["retained_read_ranks"]
    if len(set(ranks)) != len(ranks) or not set(ranks) <= {r["rank"] for r in records}:
        raise ValueError("Invalid retained ranks")
    available = set()
    for record, hit in zip(records, condition["read_hits"], strict=True):
        if any(
            hit[key] != record["request"][key] for key in ("source_id", "start_line", "end_line")
        ):
            raise ValueError("Retained hit request differs")
        if record["rank"] not in ranks:
            if hit["snippet"]:
                raise ValueError("Omitted read contains a retained snippet")
            continue
        if record["status"] != "returned":
            raise ValueError("Failed read cannot be retained")
        response = record["response"]
        if (
            hit["snippet"] != "\n".join(line["text"] for line in response["lines"])
            or hit["snippet_locator"] != response["locator"]
        ):
            raise ValueError("Retained snippet differs from returned response")
        available.update((response["id"], line["line"]) for line in response["lines"])
    return available


def attribute(review, mapping, run):
    identities = mapping["mapping"]
    if (
        [c["case_id"] for c in review["cases"]] != [c["case_id"] for c in identities]
        or len({c["task_id"] for c in identities}) != len(identities)
        or {c["id"] for c in run["cases"]} != {c["task_id"] for c in identities}
        or len(run["cases"]) != len(identities)
    ):
        raise ValueError("Case mapping differs")
    runs = {c["id"]: c for c in run["cases"]}
    rows = []
    for case, identity in zip(review["cases"], identities, strict=True):
        saved = runs[identity["task_id"]]
        if saved["source_id"] != identity["source_id"]:
            raise ValueError("Source mapping differs")
        conditions = {}
        for branch_name in ("control", "challenger"):
            branch = saved["branches"][branch_name]
            records = branch["reads"]["records"]
            for policy in POLICIES:
                for prefix in (1, 3, 5):
                    condition = branch["conditions"][policy][f"top_{prefix}"]
                    delivered = {
                        (r["response"]["id"], line["line"])
                        for r in records[:prefix]
                        if r["status"] == "returned"
                        for line in r["response"]["lines"]
                    }
                    retained = retained_lines(records[:prefix], condition)
                    if not retained <= delivered:
                        raise ValueError("Retained read lines exceed actual delivery")
                    conditions[f"{branch_name}/{policy}/top_{prefix}"] = {
                        measure: [
                            assess_interpretation(i, available) for i in case["interpretations"]
                        ]
                        for measure, available in (
                            ("delivered_reads", delivered),
                            ("retained_reads", retained),
                        )
                    }
        rows.append(
            {
                "case_id": case["case_id"],
                "task_id": identity["task_id"],
                "source_id": identity["source_id"],
                "conditions": conditions,
            }
        )
    return rows


def execute(protocol_path, output):
    protocol_path, output = Path(protocol_path), Path(output)
    if output.exists():
        raise ValueError("Attribution output already exists")
    protocol_raw = protocol_path.read_bytes()
    protocol = _load_object(protocol_raw, "Attribution protocol")
    paths = input_paths()
    if (
        set(protocol) != {"version", "files"}
        or protocol["version"] != "masked-evidence-attribution-protocol-v1"
        or set(protocol["files"]) != set(paths)
    ):
        raise ValueError("Attribution protocol inventory differs")
    raw = {name: path.read_bytes() for name, path in paths.items()}

    if any(hashlib.sha256(raw[n]).hexdigest() != value for n, value in protocol["files"].items()):
        raise ValueError("Attribution input identity differs")

    def read(relative):
        return _load_object(raw[relative], relative)

    prefix = str(HERE.relative_to(ROOT)) + "/"
    if hashlib.sha256(raw[prefix + "reviews/stage-2-lock.json"]).hexdigest() != LOCK_SHA:
        raise ValueError("Adjudication lock identity differs")
    lock = read(prefix + "reviews/stage-2-lock.json")
    if any(digest(HERE / "reviews" / name) != value for name, value in lock["artifacts"].items()):
        raise ValueError("Adjudication lock differs")
    validator = load_module("attribution_review_validator", HERE / "validate_evidence_review.py")
    checked = validator.validate_file(HERE / "reviews/evidence-adjudicated.json")
    if checked != read(prefix + "reviews/evidence-adjudicated-validation.json"):
        raise ValueError("Adjudicated review validation differs")
    preparation = load_module("attribution_preparation", HERE / "prepare_evidence.py")
    assessment = preparation._assessment()
    _, verify = assessment._freeze(preparation.EXPERIMENT / "protocol.json")
    inventory = assessment._validated_inventory(RUN, preparation.EXPERIMENT / "protocol.json")
    grade = read("runs/financebench-page-ranking-v1-grade.json")
    receipt = read(prefix + "stage-2/receipt.json")
    if any(
        hashlib.sha256(raw[name]).hexdigest() != receipt["inputs"][key]
        for key, name in {
            "mapping": prefix + "stage-1/custodian.json",
            "run": "runs/financebench-page-ranking-v1/deterministic/run.json",
            "grade": "runs/financebench-page-ranking-v1-grade.json",
        }.items()
    ):
        raise ValueError("Masked preparation binding differs")
    if (
        grade["replay_verified"] is not True
        or grade["run_inventory"] != inventory
        or receipt["run_inventory"] != inventory
    ):
        raise ValueError("Saved run differs from replay-verified inventory")
    rows = attribute(
        read(prefix + "reviews/evidence-adjudicated.json"),
        read(prefix + "stage-1/custodian.json"),
        read("runs/financebench-page-ranking-v1/deterministic/run.json"),
    )
    if len(rows) != 6:
        raise ValueError("Frozen six-case denominator differs")
    result = {
        "version": "masked-evidence-read-attribution-v1",
        "protocol_sha256": hashlib.sha256(protocol_raw).hexdigest(),
        "selected_denominator": len(rows),
        "financial_accuracy": "not_measured",
        "new_retrieval_or_read_calls": 0,
        "cases": rows,
    }

    def verify_inputs():
        verify()
        if (
            protocol_path.read_bytes() != protocol_raw
            or any(path.read_bytes() != raw[n] for n, path in paths.items())
            or assessment._validated_inventory(RUN, preparation.EXPERIMENT / "protocol.json")
            != inventory
        ):
            raise ValueError("Attribution inputs changed")

    encoded = (json.dumps(result, indent=2) + "\n").encode()
    verify_inputs()
    with output.open("xb") as handle:
        handle.write(encoded)
    verify_inputs()
    if output.read_bytes() != encoded:
        raise ValueError("Attribution output changed")
    return result


if __name__ == "__main__":
    execute(HERE / "attribution-protocol.json", HERE / "attribution-result.json")
