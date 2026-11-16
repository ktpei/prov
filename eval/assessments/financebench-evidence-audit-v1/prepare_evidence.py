"""Build masked, exact-source evidence packets from saved reads and frozen controls."""

import hashlib
import importlib.util
import json
from pathlib import Path

from provenance.benchmarks import canonical_hash
from provenance.evidence_coverage import digest, span
from provenance.sources import Sources, locator_range

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EXPERIMENT = ROOT / "eval/assessments/financebench-page-ranking-v1"
RUN = ROOT / "runs/financebench-page-ranking-v1"
GRADE = ROOT / "runs/financebench-page-ranking-v1-grade.json"
LOCK_SHA = "95eda4fee33611ece82b5ad93b88e5641e3fc8f4c768f94877f5a180bc8b2927"
RECEIPT_SHA = "4b55467d4cdb13d30363f57663f4e504f6ec96abca8630cd12c8dded332d11f7"
GRADE_SHA = "3817c8358fb83b14757b79b1c684bcb81d658649cffe3aa270a40583a98893ef"


def assemble(questions, mapping, interpretations, run, packets, sources):
    """Return reviewer allowlists and separate attribution; never invoke a tool read."""
    ids = [c["case_id"] for c in questions["cases"]]
    if (
        len(ids) != 6
        or len(set(ids)) != 6
        or ids != [c["case_id"] for c in mapping["mapping"]]
        or ids != [c["case_id"] for c in interpretations["cases"]]
    ):
        raise ValueError("Masked case identity or denominator differs")
    if len(run["cases"]) != 6 or len(packets["cases"]) != 6:
        raise ValueError("Raw saved case denominator differs")
    runs = {c["id"]: c for c in run["cases"]}
    controls = {c["id"]: c for c in packets["cases"]}
    expected = {c["task_id"] for c in mapping["mapping"]}
    if len(runs) != 6 or len(controls) != 6 or set(runs) != expected or set(controls) != expected:
        raise ValueError("Saved case denominator differs")
    outputs, custody = {}, []
    for question, identity, rubric in zip(
        questions["cases"], mapping["mapping"], interpretations["cases"], strict=True
    ):
        cid, sid = identity["case_id"], identity["source_id"]
        saved, control = runs[identity["task_id"]], controls[identity["task_id"]]
        if (
            saved["source_id"] != sid
            or control["source_id"] != sid
            or saved["status"] != "complete"
        ):
            raise ValueError("Declared source or saved status differs")
        source = sources.documents[sid]
        lines = source["text"].splitlines()
        locations = source.get("line_locations")
        if not isinstance(locations, list) or len(locations) != len(lines):
            raise ValueError("Complete page mapping required")
        page_numbers = [p.get("page") if isinstance(p, dict) else None for p in locations]
        if any(type(p) is not int or p < 1 for p in page_numbers) or page_numbers != sorted(
            page_numbers
        ):
            raise ValueError("Strict ordered physical-page mappings required")
        page_count = source.get("extraction", {}).get("page_count")
        if type(page_count) is not int or set(page_numbers) != set(range(1, page_count + 1)):
            raise ValueError("Complete physical-page inventory required")
        spans, failures = {}, []

        def include(start, end, attribution, lines=lines, spans=spans):
            span([start, end], len(lines))
            spans.setdefault((start, end), []).append(attribution)

        for branch in ["control", "challenger"]:
            records = saved["branches"][branch]["reads"]["records"]
            if len(records) > 5:
                raise ValueError("Saved branch exceeds pooling depth")
            for rank, record in enumerate(records, 1):
                if (
                    type(record["rank"]) is not int
                    or record["rank"] != rank
                    or record["request"]["source_id"] != sid
                ):
                    raise ValueError("Saved rank/source differs")
                if record["status"] == "failed":
                    failures.append({"branch": branch, "rank": rank})
                    continue
                if record["status"] != "returned":
                    raise ValueError("Unknown read disposition")
                response = record["response"]
                start, end = locator_range(response["locator"])
                span([start, end], len(lines))
                request = record["request"]
                span([request["start_line"], request["end_line"]], len(lines))
                if (
                    start != request["start_line"]
                    or end > request["end_line"]
                    or response.get("sha256") != source["sha256"]
                    or response.get("original_sha256") != source["original_sha256"]
                ):
                    raise ValueError("Saved read identity or request bounds differ")
                actual = response["lines"]
                if response["id"] != sid or actual != [
                    {"line": n, "text": lines[n - 1], "original_location": locations[n - 1]}
                    for n in range(start, end + 1)
                ]:
                    raise ValueError("Saved read is not an exact source slice")
                include(start, end, {"kind": "saved_read", "branch": branch, "rank": rank})
        for ai, alternative in enumerate(control["alternatives"], 1):
            for role, ranges in alternative.items():
                for start, end in ranges:
                    include(
                        start, end, {"kind": "annotation_control", "alternative": ai, "role": role}
                    )
        ordered = sorted(
            spans,
            key=lambda bounds: (
                canonical_hash([17, "evidence-audit-evidence-v1", cid, sid, *bounds]),
                bounds,
            ),
        )

        def excerpt(start, end, lines=lines, page_numbers=page_numbers):
            return {
                "start_line": start,
                "end_line": end,
                "lines": [
                    {"line": n, "page": page_numbers[n - 1], "text": lines[n - 1]}
                    for n in range(start, end + 1)
                ],
            }

        evidence, associations, pages = [], [], set()
        for index, (start, end) in enumerate(ordered, 1):
            eid = f"E{index:03d}"
            evidence.append({"evidence_id": eid, **excerpt(start, end)})
            associations.append(
                {
                    "evidence_id": eid,
                    "start_line": start,
                    "end_line": end,
                    "attribution": spans[start, end],
                }
            )
            pages.update(page_numbers[start - 1 : end])
        page_context = []
        for page in sorted(pages):
            indices = [n for n, value in enumerate(page_numbers, 1) if value == page]
            page_context.append(
                {"page": page, "review_only": True, **excerpt(indices[0], indices[-1])}
            )
        outputs[f"{cid}.json"] = {
            "stage": "masked_evidence_review",
            "case_id": cid,
            "question": question["question"],
            "source": {
                key: source.get(key)
                for key in ["id", "title", "company", "url", "sha256", "original_sha256"]
            },
            "interpretations": [
                {
                    key: interpretation[key]
                    for key in [
                        "id",
                        "description",
                        "assumptions",
                        "unresolved_ambiguities",
                        "required_facts",
                    ]
                }
                for interpretation in rubric["interpretations"]
            ],
            "excerpts": evidence,
            "review_only_pages": page_context,
            "scope_note": "Excerpt origins and outcomes are masked. Full native pages are review-only context, never delivered-evidence credit. Extraction is not independently visually validated; do not assume exhaustive support or correct table alignment.",
        }
        custody.append(
            {
                "case_id": cid,
                "task_id": identity["task_id"],
                "source_id": sid,
                "excerpts": associations,
                "failed_reads": failures,
                "review_only_pages": sorted(pages),
            }
        )
    return outputs, {"cases": custody}


def _assessment():
    spec = importlib.util.spec_from_file_location(
        "masked_evidence_experiment", EXPERIMENT / "assess.py"
    )
    assessment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assessment)
    return assessment


def prepare():
    assessment = _assessment()
    _, verify_experiment = assessment._freeze(EXPERIMENT / "protocol.json")
    base = assessment._base()
    paths = {
        "builder": Path(__file__),
        "plan": HERE / "plan.md",
        "instructions": HERE / "evidence-review-instructions.md",
        "stage1_lock": HERE / "reviews/stage-1-lock.json",
        "stage1_receipt": HERE / "stage-1/receipt.json",
        "questions": HERE / "stage-1/questions.json",
        "mapping": HERE / "stage-1/custodian.json",
        "interpretations": HERE / "reviews/reconciliation-c.json",
        "run": RUN / "deterministic/run.json",
        "grade": GRADE,
        "packets": base.PACKETS,
    }
    raw = {key: path.read_bytes() for key, path in paths.items()}
    hashes = {key: hashlib.sha256(value).hexdigest() for key, value in raw.items()}
    if (
        hashes["stage1_lock"] != LOCK_SHA
        or hashes["stage1_receipt"] != RECEIPT_SHA
        or hashes["grade"] != GRADE_SHA
    ):
        raise ValueError("Locked interpretation or grade identity differs")
    lock, receipt = json.loads(raw["stage1_lock"]), json.loads(raw["stage1_receipt"])
    if any(digest(HERE / name) != value for name, value in lock["inputs"].items()) or any(
        digest(HERE / "stage-1" / name) != value for name, value in receipt["outputs"].items()
    ):
        raise ValueError("Stage-1 locked input changed")
    stage1_paths = {
        "inputs": base.PREPARED / "inputs.json",
        "builder": HERE / "prepare_interpretation.py",
        "plan": HERE / "plan.md",
        "instructions": HERE / "reviewer-instructions.md",
    }
    if any(digest(path) != receipt["inputs"][name] for name, path in stage1_paths.items()):
        raise ValueError("Frozen stage-1 preparation dependency changed")
    inventory = assessment._validated_inventory(RUN, EXPERIMENT / "protocol.json")
    grade = json.loads(raw["grade"])
    if grade["replay_verified"] is not True or grade["run_inventory"] != inventory:
        raise ValueError("Saved evidence is not bound to replay-verified grade")
    outputs, custody = assemble(
        *(
            json.loads(raw[key])
            for key in ["questions", "mapping", "interpretations", "run", "packets"]
        ),
        Sources(base.CORPUS),
    )

    def verify():
        verify_experiment()
        if (
            any(path.read_bytes() != raw[key] for key, path in paths.items())
            or assessment._validated_inventory(RUN, EXPERIMENT / "protocol.json") != inventory
        ):
            raise ValueError("Evidence preparation input changed")
        if any(digest(path) != receipt["inputs"][name] for name, path in stage1_paths.items()):
            raise ValueError("Frozen stage-1 preparation dependency changed")
        if any(digest(HERE / name) != value for name, value in lock["inputs"].items()):
            raise ValueError("Interpretation dependency changed")

    verify()
    destination = HERE / "stage-2"
    destination.mkdir(exist_ok=False)
    (destination / "reviewer").mkdir()
    encoded = {
        f"reviewer/{name}": (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
        for name, value in outputs.items()
    }
    encoded["custodian.json"] = (json.dumps(custody, indent=2) + "\n").encode()
    result = {
        "version": "masked-evidence-preparation-v1",
        "inputs": hashes,
        "run_inventory": inventory,
        "outputs": {name: hashlib.sha256(data).hexdigest() for name, data in encoded.items()},
        "cases": len(outputs),
        "new_retrieval_or_read_calls": 0,
    }
    encoded["receipt.json"] = (json.dumps(result, indent=2) + "\n").encode()
    for name, data in encoded.items():
        with (destination / name).open("xb") as handle:
            handle.write(data)
    verify()
    if {str(p.relative_to(destination)) for p in destination.rglob("*") if p.is_file()} != set(
        encoded
    ) or any((destination / name).read_bytes() != data for name, data in encoded.items()):
        raise ValueError("Final masked evidence artifacts changed")
    return result


if __name__ == "__main__":
    print(json.dumps(prepare()))
