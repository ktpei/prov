"""Explicitly paid development experiment with a durable aggregate spend ledger.

A pending attempt retains its entire reservation after interruption. This runner
never retries it automatically. Gold answers are used only after the agent run.
"""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from provenance.agent import Limits, Trace
from provenance.controls import positive
from provenance.evaluation import grade_packet_answer
from provenance.graph import run_graph
from provenance.langchain_model import OpenRouterModel
from provenance.sources import Sources


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--tasks", nargs="+", required=True)
    spending = parser.add_mutually_exclusive_group(required=True)
    spending.add_argument("--budget-usd", type=float)
    spending.add_argument("--no-spend-limit", action="store_true")
    parser.add_argument("--per-task-usd", type=float, default=None)
    parser.add_argument("--output", type=Path, required=True, help="New experiment directory")
    args = parser.parse_args()
    if args.no_spend_limit:
        if args.per_task_usd is not None:
            parser.error("--per-task-usd cannot accompany --no-spend-limit")
    else:
        positive(args.budget_usd, "aggregate budget")
        args.per_task_usd = 0.05 if args.per_task_usd is None else args.per_task_usd
        positive(args.per_task_usd, "task budget")
    benchmark_content = args.benchmark.read_bytes()
    benchmark = json.loads(benchmark_content)
    task_rows = benchmark["tasks"]
    benchmark_task_ids = [task["id"] for task in task_rows]
    if len(set(benchmark_task_ids)) != len(benchmark_task_ids):
        parser.error("Benchmark task IDs must be unique")
    tasks = {task["id"]: task for task in task_rows}
    if len(set(args.tasks)) != len(args.tasks) or not set(args.tasks) <= tasks.keys():
        parser.error("Select unique known development task IDs")
    if any(tasks[key].get("split") != "dev" for key in args.tasks):
        parser.error("Paid experiment preflight requires explicit development task labels")
    sources = Sources(args.corpus)
    corpus_hashes = {source_id: source["sha256"] for source_id, source in sources.documents.items()}
    if not benchmark["source_hashes"] or benchmark["source_hashes"] != corpus_hashes:
        raise ValueError("Benchmark/corpus hash mismatch")
    # Fail closed on an existing experiment, including any pending reservation.
    args.output.mkdir(parents=True, exist_ok=False)
    model = OpenRouterModel(
        os.environ.get("OPENROUTER_API_KEY"),
        os.environ.get("OPENROUTER_MODEL"),
        os.environ.get("OPENROUTER_INPUT_USD_PER_MILLION"),
        os.environ.get("OPENROUTER_OUTPUT_USD_PER_MILLION"),
        max_output=4000,
    )
    ledger_path = args.output / "experiment.json"
    ledger = {
        "mode": "live_openrouter_development",
        "model": model.name,
        "budget_usd": args.budget_usd,
        "spend_limit_enabled": not args.no_spend_limit,
        "accounted_cost_usd": 0,
        "pricing": {
            "input_usd_per_million": model.input_rate,
            "output_usd_per_million": model.output_rate,
        },
        "benchmark_version": benchmark["version"],
        "benchmark_content_sha256": hashlib.sha256(benchmark_content).hexdigest(),
        "source_hashes": benchmark["source_hashes"],
        "selection_metadata": {
            "selected_task_ids": list(args.tasks),
            "selection_status": [
                {"task_id": task_id, "status": "not_started"} for task_id in args.tasks
            ],
        },
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True)
        ),
        "attempts": [],
        "status": "running",
        "limitation": "Application-side reservations are estimates, not a provider billing guarantee. Semantic support requires review.",
    }
    write_json(ledger_path, ledger)
    selection_status = {
        item["task_id"]: item for item in ledger["selection_metadata"]["selection_status"]
    }

    def skip_not_started_tasks():
        for item in selection_status.values():
            if item["status"] == "not_started":
                item["status"] = "skipped"

    for task_id in args.tasks:
        remaining = (
            args.budget_usd - ledger["accounted_cost_usd"] if args.budget_usd is not None else None
        )
        if remaining is not None and remaining <= 1e-9:
            ledger["status"] = "aggregate_budget_exhausted"
            skip_not_started_tasks()
            break
        reservation = min(args.per_task_usd, remaining) if remaining is not None else None
        reserved_cost = reservation if reservation is not None else 0
        attempt = {
            "task_id": task_id,
            "status": "pending",
            "reserved_usd": reservation,
            "accounted_cost_usd": reserved_cost,
            "cost_uncertain": reservation is None,
        }
        ledger["attempts"].append(attempt)
        ledger["accounted_cost_usd"] += reserved_cost
        selection_status[task_id]["status"] = "pending"
        write_json(ledger_path, ledger)  # Persist before any potentially paid request.
        print(
            json.dumps({"task_id": task_id, "status": "starting", "reserved_usd": reservation}),
            flush=True,
        )
        task = tasks[task_id]
        report = run_graph(
            task["question"],
            model,
            Sources(args.corpus),
            Limits(
                max_model_calls=10,
                max_tool_calls=12,
                timeout_seconds=180,
                request_timeout_seconds=45,
                budget_usd=reservation,
            ),
            Trace(args.output / "runs"),
        )
        actual = report["metrics"]["accounted_cost_usd"]
        ledger["accounted_cost_usd"] += actual - reserved_cost
        # Persist known settlement before postprocessing, which can independently fail.
        result_path = args.output / f"{task_id}.json"
        write_json(result_path, report)
        attempt.update(
            status=report["status"],
            accounted_cost_usd=actual,
            metrics=report["metrics"],
            cost_uncertain=report["metrics"]["cost_uncertain"],
            stop_reason=report["stop_reason"],
            result_file=result_path.name,
        )
        selection_status[task_id]["status"] = report["status"]
        write_json(ledger_path, ledger)
        grading = grade_packet_answer(task, report, directory=args.corpus)
        attempt["grading"] = grading
        write_json(ledger_path, ledger)
        print(
            json.dumps(
                {
                    "task_id": task_id,
                    "status": report["status"],
                    "cost_usd": actual,
                    "mechanical_checks_passed": grading["mechanical_checks_passed"],
                    "stop_reason": report["stop_reason"],
                }
            ),
            flush=True,
        )
        if report["metrics"]["cost_uncertain"] or (
            args.budget_usd is not None and ledger["accounted_cost_usd"] > args.budget_usd
        ):
            ledger["status"] = "stopped_for_billing_review"
            skip_not_started_tasks()
            break
    if ledger["status"] == "running":
        ledger["status"] = "finished"
    write_json(ledger_path, ledger)
    print(
        json.dumps(
            {
                "status": ledger["status"],
                "accounted_cost_usd": ledger["accounted_cost_usd"],
                "ledger": str(ledger_path),
            }
        )
    )


if __name__ == "__main__":
    main()
