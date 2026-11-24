"""Explicit continuation of untouched cases, never retrying a dispatched task."""

import copy
import json
from pathlib import Path

from provenance.benchmarks import canonical_hash


def continue_ledger(ledger, prior_path, *, rows_key, retain_uncertain, policy_keys=()):
    prior = json.loads(Path(prior_path).read_text())
    if prior.get("status") not in {
        "stopped_for_billing_review",
        "interrupted",
        "aggregate_budget_exhausted",
    }:
        raise ValueError("Only a stopped, settled batch can continue in a new directory")
    keys = ["prepared_sha256", "mode", "pricing", "budget_usd"]
    if rows_key == "records":
        keys.append("profile")
        for key in policy_keys:
            if prior["policy"].get(key) != ledger["policy"].get(key):
                raise ValueError(f"Continuation policy mismatch: {key}")
        # The driver may gain continuation support, but inference behavior stays frozen.
        for name, digest in prior["policy"]["implementation_sha256"].items():
            if (
                name != "daloopa_run.py"
                and ledger["policy"]["implementation_sha256"].get(name) != digest
            ):
                raise ValueError(f"Continuation runtime changed: {name}")
    else:
        keys += [
            "model",
            "prompt_version",
            "generation",
            "instructions",
            "inputs_sha256",
            "per_task_usd",
            "timeout_seconds",
        ]
    for key in keys:
        if prior.get(key) != ledger.get(key):
            raise ValueError(f"Continuation mismatch: {key}")
    if [r["id"] for r in prior[rows_key]] != [r["id"] for r in ledger[rows_key]]:
        raise ValueError("Continuation selection mismatch")
    if any(r["status"] in {"pending", "not_started"} for r in prior[rows_key]):
        raise ValueError("Unsettled batch cannot continue; review pending requests first")
    uncertain = [r for r in prior[rows_key] if r.get("cost_uncertain")]
    if uncertain and not retain_uncertain:
        raise ValueError(
            "Review billing and explicitly retain uncertain reservations before continuing"
        )
    rows = copy.deepcopy(prior[rows_key])
    remaining = 0
    for row in rows:
        if row["status"] == "skipped":
            if row.get("accounted_cost_usd") or row.get("input") or row.get("report"):
                raise ValueError("A previously dispatched task cannot be restarted")
            task_id = row["id"]
            row.clear()
            row.update(id=task_id, status="not_started")
            remaining += 1
    if not remaining:
        raise ValueError("No untouched cases remain")
    ledger[rows_key] = rows
    ledger["accounted_cost_usd"] = prior["accounted_cost_usd"]
    ledger["continuations"] = [
        *prior.get("continuations", []),
        {
            "prior_path": str(Path(prior_path).resolve()),
            "prior_submission_sha256": canonical_hash(prior),
            "prior_policy": prior.get("policy"),
            "untouched_cases": remaining,
            "retained_uncertain_records": {r["id"]: canonical_hash(r) for r in uncertain},
            "review": "Retain conservative reservations and failed outcomes; never retry dispatched cases.",
        },
    ]
    return ledger


def reviewed_uncertainty(ledger, rows_key="records"):
    reviewed = {}
    for continuation in ledger.get("continuations", []):
        reviewed.update(continuation.get("retained_uncertain_records", {}))
    return all(
        reviewed.get(row["id"]) == canonical_hash(row)
        for row in ledger[rows_key]
        if row.get("cost_uncertain")
    )
