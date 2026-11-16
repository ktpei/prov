"""One durable, interleaved task-by-arm comparison; no retry or automatic resume."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from provenance.benchmark_run import INSTRUCTIONS, parse_output
from provenance.benchmarks import canonical_hash, load_bundle, score_run
from provenance.comparison_model import ComparisonClient, ComparisonIntegrityError, clone
from provenance.controls import Budget, LimitReached, deadline, positive
from provenance.experiment import write_json
from provenance.transport import ProviderError, post_json


def settle_row(ledger, row, budget, model, started):
    previous = row["accounted_cost_usd"]
    row.update(
        accounted_cost_usd=budget.charged,
        cost_uncertain=budget.uncertain,
        dispatched=model.last_dispatched,
        latency_seconds=time.monotonic() - started,
    )
    ledger["accounted_cost_usd"] += budget.charged - previous
    ledger["arm_accounted_cost_usd"][row["arm_id"]] += budget.charged - previous


def run_comparison(
    bundle,
    arms,
    output,
    *,
    key,
    budget_usd,
    per_arm_usd,
    per_attempt_usd,
    max_output,
    timeout=120,
    request=post_json,
):
    """Live caller must first reconcile authorization, capability and account billing."""
    for value, label in (
        (budget_usd, "comparison budget"),
        (per_arm_usd, "arm budget"),
        (per_attempt_usd, "attempt budget"),
        (timeout, "timeout"),
    ):
        positive(value, label)
    bundle, arms = clone(bundle), clone(arms)
    manifest = bundle["manifest"]
    prepared_hash = canonical_hash(manifest)
    score_run(bundle, {"prepared_sha256": prepared_hash, "predictions": []})
    if manifest["source"]["dataset"] == "tatqa":
        from provenance.official_metrics import load_tatqa_metric

        load_tatqa_metric()
    if manifest["condition"] == "full_agent" or manifest["source"]["dataset"] == "convfinqa":
        raise ValueError("Comparison v1 supports independent tool-free requests only")
    if not isinstance(arms, list) or len(arms) < 2:
        raise ValueError("Comparison needs at least two arms")
    clients = {}
    for arm in arms:
        if not isinstance(arm, dict) or set(arm) != {"id", "capability", "effort", "temperature"}:
            raise ValueError("Invalid comparison arm")
        identifier = arm["id"]
        if not isinstance(identifier, str) or not identifier.strip() or identifier in clients:
            raise ValueError("Duplicate or invalid arm ID")
        clients[identifier] = ComparisonClient(
            key,
            arm["capability"],
            effort=arm["effort"],
            temperature=arm["temperature"],
            max_output=max_output,
            instructions=INSTRUCTIONS,
            request=request,
        )
    arm_ids = list(clients)
    references = {task["id"]: task["reference"] for task in bundle["tasks"]}
    rows = []
    for index, payload in enumerate(bundle["inputs"]):
        for offset in range(len(arm_ids)):
            identifier = arm_ids[(index + offset) % len(arm_ids)]
            rows.append(
                {
                    "id": payload["id"],
                    "arm_id": identifier,
                    "status": "not_started",
                    "input_sha256": canonical_hash(payload),
                    "receipt": clients[identifier].prepare(json.dumps(payload, ensure_ascii=False)),
                }
            )
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    ledger = {
        "version": "model-effort-comparison-v1",
        "prepared_sha256": prepared_hash,
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True)
        ),
        "arm_identities": {identifier: model.identity() for identifier, model in clients.items()},
        "ordering": "task-major; rotate arm order by task index",
        "budget_usd": budget_usd,
        "per_arm_usd": per_arm_usd,
        "per_attempt_usd": per_attempt_usd,
        "timeout_seconds": timeout,
        "accounted_cost_usd": 0,
        "arm_accounted_cost_usd": dict.fromkeys(arm_ids, 0),
        "status": "running",
        "predictions": rows,
        "scoring_status": "not_run",
        "limitations": [
            "Supplied-context tool-free comparison, not full-agent accuracy.",
            "Common limits do not equate compute across models or effort labels.",
            "Provider-reported cost is distinct from invoice reconciliation.",
        ],
    }
    path = output / "comparison.json"
    write_json(path, ledger)
    for row in rows:
        if references[row["id"]].get("requires_review"):
            row.update(
                status="reference_review_required", failure="Unresolved reference; no request"
            )
            write_json(path, ledger)
            continue
        identifier = row["arm_id"]
        remaining = min(
            budget_usd - ledger["accounted_cost_usd"],
            per_arm_usd - ledger["arm_accounted_cost_usd"][identifier],
            per_attempt_usd,
        )
        if remaining <= 1e-12:
            row.update(status="skipped", failure="comparison_or_arm_budget_exhausted")
            write_json(path, ledger)
            continue
        row.update(status="pending", reserved_usd=remaining, accounted_cost_usd=remaining)
        ledger["accounted_cost_usd"] += remaining
        ledger["arm_accounted_cost_usd"][identifier] += remaining
        write_json(path, ledger)  # All arm reservations share this durable inventory.
        budget = Budget(remaining)
        model = clients[identifier]
        model.last_dispatched, model.last_response = False, None
        started = time.monotonic()
        stop = None
        try:
            with deadline(timeout) as left:
                response = model.execute(row["receipt"], left(), budget)
            row["response"] = response
            row["status"] = response["status"]
            settle_row(ledger, row, budget, model, started)
            write_json(path, ledger)  # Retain known billing before parsing model content.
            if response["status"] == "completed":
                adapted = {
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": response["output_text"]}],
                        }
                    ],
                }
                try:
                    parsed, parse_status = parse_output(
                        adapted, structured=manifest["source"]["dataset"] != "financebench"
                    )
                except RecursionError:
                    parsed, parse_status = None, "invalid_json_depth"
                row.update(output=parsed, parse_status=parse_status)
            else:
                row["failure"] = "Provider output incomplete or empty"
        except (ProviderError, LimitReached) as exc:
            row.update(
                status="failed", failure=str(exc), rejected_provider_response=model.last_response
            )
            if isinstance(exc, ComparisonIntegrityError):
                stop = "stopped_for_integrity_review"
        # Process death/interruption leaves the full durable pending reservation.
        settle_row(ledger, row, budget, model, started)
        if (
            budget.uncertain
            or ledger["accounted_cost_usd"] > budget_usd + 1e-12
            or ledger["arm_accounted_cost_usd"][identifier] > per_arm_usd + 1e-12
        ):
            stop = "stopped_for_billing_review"
        if stop:
            ledger["status"] = stop
        write_json(path, ledger)  # Known cost persists before scoring or later failures.
        if stop:
            break
    if ledger["status"] == "running":
        ledger["status"] = "finished"
    for row in rows:
        if row["status"] == "not_started":
            row.update(status="skipped", failure=ledger["status"])
    write_json(path, ledger)
    scores = {
        identifier: score_run(
            bundle,
            {
                "prepared_sha256": prepared_hash,
                "predictions": [row for row in rows if row["arm_id"] == identifier],
            },
        )
        for identifier in arm_ids
    }
    write_json(output / "scores.json", scores)
    ledger["scoring_status"] = "finished"
    write_json(path, ledger)
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--arms-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget-usd", type=float, required=True)
    parser.add_argument("--per-arm-usd", type=float, required=True)
    parser.add_argument("--per-attempt-usd", type=float, required=True)
    parser.add_argument("--max-output-tokens", type=int, required=True)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    result = run_comparison(
        load_bundle(args.prepared),
        json.loads(args.arms_json.read_text()),
        args.output,
        key=os.environ.get("OPENROUTER_API_KEY"),
        budget_usd=args.budget_usd,
        per_arm_usd=args.per_arm_usd,
        per_attempt_usd=args.per_attempt_usd,
        max_output=args.max_output_tokens,
        timeout=args.timeout,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "attempts": len(result["predictions"]),
                "accounted_cost_usd": result["accounted_cost_usd"],
            }
        )
    )


if __name__ == "__main__":
    main()
