"""Reproduce and compare completed Daloopa arms with identical tasks and budgets.

Run as a module: python -m eval.scripts.compare_navigation --help
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from provenance.benchmarks import canonical_hash
from provenance.daloopa import load
from provenance.daloopa_score import check_quotes, score


def compare(bundle, baseline, candidate):
    for ledger in (baseline, candidate):
        if ledger["status"] != "finished" or any(
            row.get("cost_uncertain") for row in ledger["records"]
        ):
            raise ValueError("Compare finished, settled runs only")
    for key in ("prepared_sha256", "profile", "pricing", "budget_usd"):
        if baseline[key] != candidate[key]:
            raise ValueError(f"Comparison mismatch: {key}")
    for key in (
        "model",
        "limits",
        "max_output_tokens",
        "source_access",
        "corpus_manifest_sha256",
        "exa_request_cap",
    ):
        if baseline["policy"][key] != candidate["policy"][key]:
            raise ValueError(f"Policy mismatch: {key}")
    scores = [score(bundle, ledger) for ledger in (baseline, candidate)]
    quick = set(bundle["manifest"]["quick_ids"])
    selected = set(bundle["manifest"][f"{baseline['profile']}_ids"])
    groups = {"all_selected": selected}
    if baseline["profile"] == "full":
        groups.update(quick25=quick, outside_quick=selected - quick)
    report = {"version": "paired-navigation-v1", "profile": baseline["profile"], "groups": {}}
    report["submission_hashes"] = [canonical_hash(ledger) for ledger in (baseline, candidate)]
    for group, ids in groups.items():
        arms = []
        for ledger, scored in zip((baseline, candidate), scores, strict=True):
            rows = [r for r in ledger["records"] if r["id"] in ids]
            grades = [r for r in scored["tasks"] if r["id"] in ids]
            answerable = sum(
                bool((r.get("report", {}).get("answer") or {}).get("answerable")) for r in rows
            )
            quote_checks = []
            for row in rows:
                if row["status"] != "completed" or not (
                    row.get("report", {}).get("answer") or {}
                ).get("answerable"):
                    continue
                try:
                    quote_checks.append(check_quotes(row))
                except (ValueError, KeyError, TypeError):
                    quote_checks.append(False)
            tool_counts = Counter(
                event["call"]["name"]
                for r in rows
                for event in r.get("report", {}).get("events", [])
                if event.get("event") == "tool_request"
            )
            arms.append(
                {
                    "navigation": ledger["policy"].get("navigation", "baseline"),
                    "selected": len(rows),
                    "scorable": sum(r["numeric_exact"] is not None for r in grades),
                    "exact": sum(r["numeric_exact"] is True for r in grades),
                    "within_1pct": sum(r["tolerance_1pct"] is True for r in grades),
                    "numeric_answers": answerable,
                    "quote_valid": sum(quote_checks),
                    "quote_invalid": len(quote_checks) - sum(quote_checks),
                    "statuses": dict(Counter(r["status"] for r in rows)),
                    "stops": dict(
                        Counter(
                            r["report"].get("stop_reason")
                            for r in rows
                            if r.get("report", {}).get("stop_reason")
                        )
                    ),
                    "tool_requests": dict(tool_counts),
                    "cost_usd": sum(r.get("accounted_cost_usd", 0) for r in rows),
                    "task_seconds": sum(
                        r.get("report", {}).get("metrics", {}).get("latency_seconds", 0)
                        for r in rows
                    ),
                }
            )
        paired = {}
        for metric in ("numeric_exact", "tolerance_1pct"):
            transitions = Counter()
            changed = []
            for before, after in zip(scores[0]["tasks"], scores[1]["tasks"], strict=True):
                if before["id"] != after["id"]:
                    raise ValueError("Task alignment mismatch")
                if before["id"] not in ids or before[metric] is None:
                    continue
                label = (
                    ("pass" if before[metric] else "fail")
                    + "_to_"
                    + ("pass" if after[metric] else "fail")
                )
                transitions[label] += 1
                if before[metric] != after[metric]:
                    changed.append({"id": before["id"], "transition": label})
            paired[metric] = {"transitions": dict(transitions), "changed": changed}
        report["groups"][group] = {"arms": arms, "paired": paired}
    report["limitations"] = [
        "Combined ingestion/navigation treatment; live retrieval and provider nondeterminism remain confounders.",
        "Public development questions; outside-quick results are not guaranteed issuer-unseen.",
        "Quote validity is not semantic financial support; no human-supported accuracy inferred.",
    ]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prepared", "baseline", "candidate", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = compare(
        load(args.prepared),
        json.loads(args.baseline.read_text()),
        json.loads(args.candidate.read_text()),
    )
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["groups"]["all_selected"]["arms"], indent=2))


if __name__ == "__main__":
    main()
