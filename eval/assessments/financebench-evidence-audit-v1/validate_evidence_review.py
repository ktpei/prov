"""Check review identities and literal citations, not financial sufficiency."""

import argparse
import hashlib
import json
from pathlib import Path

from eval.scripts.table_assessment_run import _load_object, _require_exact_keys

HERE = Path(__file__).resolve().parent
RECEIPT_SHA = "6b7c397a9df2b69938584a999216e1d88273fc08a4387dad081c93aab71d62da"
STATUSES = {"supported", "partial", "unsupported", "conflicting", "conditional"}


def validate(review, packets, hashes):
    _require_exact_keys(
        review,
        {
            "stage",
            "reviewer",
            "input_sha256",
            "cases",
            "outside_access",
            "recognition_or_prior_knowledge",
        },
        "Evidence review",
    )
    if (
        review["stage"] != "masked_evidence_review"
        or not isinstance(review["reviewer"], str)
        or not review["reviewer"].strip()
        or review["input_sha256"] != hashes
    ):
        raise ValueError("Review stage, identity or input hashes differ")
    if not isinstance(review["outside_access"], (str, list, dict)):
        raise ValueError("Outside-access disclosure must be text, a list or an object")
    expected = [p["case_id"] for p in packets]
    if (
        len(expected) != 6
        or len(set(expected)) != 6
        or [c["case_id"] for c in review["cases"]] != expected
    ):
        raise ValueError("Review must preserve all six case identities/order")
    totals = {
        "cases": 6,
        "interpretations": 0,
        "requirements": 0,
        "complete_sets": 0,
        "citations": 0,
        "review_only_citations": 0,
    }
    for case, packet in zip(review["cases"], packets, strict=True):
        _require_exact_keys(
            case, {"case_id", "interpretations", "source_uncertainty"}, "Review case"
        )
        lines = {}
        for item in [*packet["excerpts"], *packet["review_only_pages"]]:
            for line in item["lines"]:
                if line["line"] in lines and lines[line["line"]] != line["text"]:
                    raise ValueError("Packet has inconsistent source text")
                lines[line["line"]] = line["text"]
        excerpts = {
            e["evidence_id"]: {line["line"] for line in e["lines"]} for e in packet["excerpts"]
        }
        pooled = set().union(*excerpts.values())

        def check_citation(citation, lines=lines, excerpts=excerpts, pooled=pooled, packet=packet):
            _require_exact_keys(
                citation,
                {
                    "source_id",
                    "start_line",
                    "end_line",
                    "text_quote",
                    "evidence_ids",
                    "review_only_context",
                },
                "Evidence citation",
            )
            start, end = citation["start_line"], citation["end_line"]
            if (
                type(start) is not int
                or type(end) is not int
                or not 1 <= start <= end <= max(lines, default=0)
            ):
                raise ValueError("Citation bounds must be strict positive integers")
            selected = set(range(start, end + 1))
            if citation["source_id"] != packet["source"]["id"] or not selected <= lines.keys():
                raise ValueError("Citation source/range is outside supplied packet")
            quote = citation["text_quote"]
            if (
                not isinstance(quote, str)
                or not quote.strip()
                or quote not in "\n".join(lines[n] for n in range(start, end + 1))
            ):
                raise ValueError(
                    f"Citation quote is not literal source text at {packet['case_id']} L{start}-L{end}"
                )
            ids = citation["evidence_ids"]
            if (
                not isinstance(ids, list)
                or any(not isinstance(i, str) or i not in excerpts for i in ids)
                or len(ids) != len(set(ids))
                or any(not excerpts[i] & selected for i in ids)
            ):
                raise ValueError("Citation excerpt IDs are invalid or unrelated")
            expected_review_only = not selected <= pooled
            if (
                type(citation["review_only_context"]) is not bool
                or citation["review_only_context"] != expected_review_only
            ):
                raise ValueError("Review-only flag differs from exact excerpt union")
            if not expected_review_only and not selected <= set().union(
                *(excerpts[i] for i in ids)
            ):
                raise ValueError("Cited excerpt IDs do not cover the stated span")
            totals["citations"] += 1
            totals["review_only_citations"] += expected_review_only
            return expected_review_only

        if [i["interpretation_id"] for i in case["interpretations"]] != [
            i["id"] for i in packet["interpretations"]
        ]:
            raise ValueError("Locked interpretation order differs")
        for interpretation, rubric in zip(
            case["interpretations"], packet["interpretations"], strict=True
        ):
            totals["interpretations"] += 1
            _require_exact_keys(
                interpretation,
                {
                    "interpretation_id",
                    "requirements",
                    "complete_evidence_sets",
                    "unresolved_issues",
                    "proposed_rubric_revisions",
                },
                "Interpretation review",
            )
            expected_roles = {f["id"] for f in rubric["required_facts"]}
            requirements = interpretation["requirements"]
            if (
                len(requirements) != len(expected_roles)
                or {r["requirement_id"] for r in requirements} != expected_roles
            ):
                raise ValueError("Locked requirements are missing, duplicated or changed")
            for requirement in requirements:
                _require_exact_keys(
                    requirement,
                    {"requirement_id", "status", "reason", "spans"},
                    "Requirement review",
                )
                if (
                    requirement["status"] not in STATUSES
                    or not isinstance(requirement["reason"], str)
                    or not requirement["reason"].strip()
                    or not isinstance(requirement["spans"], list)
                ):
                    raise ValueError("Invalid requirement status/reason/spans")
                if requirement["status"] == "supported" and not requirement["spans"]:
                    raise ValueError("Supported requirement needs source citations")
                for citation in requirement["spans"]:
                    check_citation(citation)
                totals["requirements"] += 1
            complete = interpretation["complete_evidence_sets"]
            if not isinstance(complete, list) or len({s["id"] for s in complete}) != len(complete):
                raise ValueError("Complete evidence sets must have unique IDs")
            if complete and any(r["status"] != "supported" for r in requirements):
                raise ValueError("Complete set conflicts with unsupported/conditional requirements")
            for evidence_set in complete:
                _require_exact_keys(
                    evidence_set,
                    {"id", "requirements", "assumptions", "uses_review_only_context"},
                    "Complete evidence set",
                )
                if set(evidence_set["requirements"]) != expected_roles:
                    raise ValueError("Complete set must cover every locked requirement")
                context_flags = []
                for citations in evidence_set["requirements"].values():
                    if not isinstance(citations, list) or not citations:
                        raise ValueError("Complete set requires nonempty citations per role")
                    context_flags.extend(check_citation(c) for c in citations)
                if type(evidence_set["uses_review_only_context"]) is not bool or evidence_set[
                    "uses_review_only_context"
                ] != any(context_flags):
                    raise ValueError("Complete-set review-only flag differs")
                totals["complete_sets"] += 1
    return {
        "version": "evidence-review-structural-validation-v1",
        "reviewer": review["reviewer"],
        "counts": totals,
        "financial_sufficiency": "not_validated",
        "outside_access_disclosed": review["outside_access"],
    }


def validate_file(path):
    path = Path(path)
    validator_raw = Path(__file__).read_bytes()
    receipt_raw = (HERE / "stage-2/receipt.json").read_bytes()
    if hashlib.sha256(receipt_raw).hexdigest() != RECEIPT_SHA:
        raise ValueError("Locked stage-2 receipt identity differs")
    receipt = json.loads(receipt_raw)
    instructions = HERE / "evidence-review-instructions.md"
    instruction_raw = instructions.read_bytes()
    if hashlib.sha256(instruction_raw).hexdigest() != receipt["inputs"]["instructions"]:
        raise ValueError("Locked review instructions differ")
    packets, hashes, snapshots = [], {}, {instructions: instruction_raw}
    for name, expected in sorted(receipt["outputs"].items()):
        if name.startswith("reviewer/"):
            p = HERE / "stage-2" / name
            raw = p.read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError("Evidence packet hash differs")
            snapshots[p] = raw
            packets.append(_load_object(raw, "Reviewer packet"))
            hashes[p.name] = expected
    raw = path.read_bytes()
    result = validate(_load_object(raw, "Evidence review"), packets, hashes)
    if (
        Path(__file__).read_bytes() != validator_raw
        or path.read_bytes() != raw
        or (HERE / "stage-2/receipt.json").read_bytes() != receipt_raw
        or any(p.read_bytes() != data for p, data in snapshots.items())
    ):
        raise ValueError("Review validation inputs changed")
    return {
        **result,
        "review_sha256": hashlib.sha256(raw).hexdigest(),
        "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
        "validator_sha256": hashlib.sha256(validator_raw).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review")
    args = parser.parse_args()
    print(json.dumps(validate_file(args.review), indent=2))
