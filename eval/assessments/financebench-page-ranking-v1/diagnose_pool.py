"""Post-hoc evaluator-only saved-pool oracle; never a retrieval policy or model input."""

import importlib.util
import itertools
import json
from pathlib import Path

from provenance.evidence_coverage import digest, span
from provenance.sources import Sources

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT / "runs/financebench-page-ranking-v1"
GRADE = ROOT / "runs/financebench-page-ranking-v1-grade.json"


def minimum_cover(windows, required):
    """Return the first minimum-cardinality witness up to five reads, without gaps."""
    if not required:
        raise ValueError("Oracle requires nonempty evidence")
    if len(windows) > 25:
        raise ValueError("Oracle supports the frozen pool limit only")
    missing = required - set().union(*windows)
    if missing:
        return {"status": "missing_from_pool", "missing_lines": sorted(missing), "ranks": None}
    # A bit per required line allows different windows to cover parts of one role.
    bits = {line: 1 << i for i, line in enumerate(sorted(required))}
    masks = [sum(bits[line] for line in window & required) for window in windows]
    target = (1 << len(bits)) - 1
    for size in range(1, min(5, len(windows)) + 1):
        for selected in itertools.combinations(range(len(windows)), size):
            union = 0
            for index in selected:
                union |= masks[index]
            if union == target:
                return {
                    "status": "coverable_within_five",
                    "missing_lines": [],
                    "ranks": [i + 1 for i in selected],
                }
    return {"status": "pool_complete_requires_more_than_five", "missing_lines": [], "ranks": None}


def diagnose():
    spec = importlib.util.spec_from_file_location("saved_pool_assessment", HERE / "assess.py")
    assessment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assessment)
    _, verify = assessment._freeze(HERE / "protocol.json")
    inventory = assessment._validated_inventory(RUN, HERE / "protocol.json")
    summary_raw = (HERE / "result.json").read_bytes()
    summary = json.loads(summary_raw)
    if digest(GRADE) != summary["grade_sha256"]:
        raise ValueError("Saved grade differs from published result")
    grade = json.loads(GRADE.read_bytes())
    if grade["replay_verified"] is not True or grade["run_inventory"] != inventory:
        raise ValueError("Saved pool is not bound to the verified grade")
    state = json.loads((RUN / "deterministic/run.json").read_bytes())
    base = assessment._base()
    packets = json.loads(base.PACKETS.read_bytes())
    sources = Sources(base.CORPUS)
    for case in state["cases"]:
        for rank, candidate in enumerate(case["ranking"]["candidates"], 1):
            if type(candidate.get("passage_rank")) is not int or candidate["passage_rank"] != rank:
                raise ValueError("Saved candidate rank differs from ordered pool")
    rows = [
        {
            "id": c["id"],
            "retrieved_hits": [
                {
                    "source_id": h["source_id"],
                    "start_line": h["start_line"],
                    "end_line": h["end_line"],
                    "snippet": "",
                }
                for h in c["ranking"]["candidates"]
            ],
        }
        for c in state["cases"]
    ]
    # Revalidate packet shape and exact declared-source pool ranges; no new search.
    observed = assessment.pool_coverage(packets["cases"], rows, sources)
    if observed != grade["pool_25"]:
        raise ValueError("Saved pool coverage differs from verified grade")
    cases = []
    for packet, case, row in zip(packets["cases"], state["cases"], rows, strict=True):
        line_count = len(sources.documents[packet["source_id"]]["text"].splitlines())
        windows = [
            span([h["start_line"], h["end_line"]], line_count) for h in row["retrieved_hits"]
        ]
        available = set().union(*windows)
        alternatives = []
        for index, alternative in enumerate(packet["alternatives"], 1):
            roles = {
                role: set().union(*(span(s, line_count) for s in ranges))
                for role, ranges in alternative.items()
            }
            witness = minimum_cover(windows, set().union(*roles.values()))
            alternatives.append(
                {
                    "alternative": index,
                    **witness,
                    "missing_by_role": {
                        role: sorted(lines - available) for role, lines in roles.items()
                    },
                    "witness_windows": [
                        row["retrieved_hits"][rank - 1] for rank in witness["ranks"] or []
                    ],
                }
            )
        eligible = [a for a in alternatives if a["ranks"] is not None]
        best = (
            min(eligible, key=lambda a: (len(a["ranks"]), tuple(a["ranks"]), a["alternative"]))
            if eligible
            else None
        )
        status = (
            "ineligible"
            if packet["disposition"] != "mapped"
            else "coverable_within_five"
            if best is not None
            else "pool_complete_requires_more_than_five"
            if any(a["status"] == "pool_complete_requires_more_than_five" for a in alternatives)
            else "missing_from_pool"
        )
        cases.append(
            {
                "id": case["id"],
                "source_id": case["source_id"],
                "disposition": packet["disposition"],
                "status": status,
                "minimum_windows_within_five": len(best["ranks"]) if best else None,
                "case_witness": {"alternative": best["alternative"], "ranks": best["ranks"]}
                if best
                else None,
                "alternatives": alternatives,
            }
        )
    verify()
    if (
        assessment._validated_inventory(RUN, HERE / "protocol.json") != inventory
        or digest(GRADE) != summary["grade_sha256"]
        or (HERE / "result.json").read_bytes() != summary_raw
    ):
        raise ValueError("Diagnostic inputs changed")
    return {
        "version": "saved-pool-oracle-diagnosis-v1",
        "diagnostic_sha256": digest(__file__),
        "grade_sha256": digest(GRADE),
        "protocol_sha256": digest(HERE / "protocol.json"),
        "run_inventory": inventory,
        "selected_denominator": len(cases),
        "max_reads": 5,
        "tie_rule": "minimum cardinality, then lexicographic original rank tuple, then alternative index",
        "oracle_uses_evaluator_labels": True,
        "new_retrieval_or_read_calls": 0,
        "cases": cases,
        "limitation": "Post-hoc exact frozen-location parent opportunity; label-dependent witness is not a deployable selection policy or delivered/retained evidence.",
    }


if __name__ == "__main__":
    result = diagnose()
    with (HERE / "pool-diagnosis.json").open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({c["id"]: [a["status"] for a in c["alternatives"]] for c in result["cases"]}))
