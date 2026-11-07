"""Explicitly paid development experiment with a durable aggregate spend ledger.

A pending attempt retains its entire reservation after interruption. This runner
never retries it automatically. Gold answers are used only after the agent run.
"""

import argparse
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
    parser.add_argument("--budget-usd", type=float, required=True)
    parser.add_argument("--per-task-usd", type=float, default=0.05)
    parser.add_argument("--output", type=Path, required=True, help="New experiment directory")
    args = parser.parse_args()
    positive(args.budget_usd, "aggregate budget")
    positive(args.per_task_usd, "task budget")
    benchmark = json.loads(args.benchmark.read_text())
    tasks = {task["id"]: task for task in benchmark["tasks"]}
    if len(set(args.tasks)) != len(args.tasks) or not set(args.tasks) <= tasks.keys():
        parser.error("Select unique known development task IDs")
    if any(tasks[key].get("split", "dev") != "dev" for key in args.tasks):
        parser.error("Only development tasks may be run")
    # Fail closed on an existing experiment, including any pending reservation.
    args.output.mkdir(parents=True, exist_ok=False)
    model = OpenRouterModel(
        os.environ.get("OPENROUTER_API_KEY"),
        os.environ.get("OPENROUTER_MODEL"),
        os.environ.get("OPENROUTER_INPUT_USD_PER_MILLION"),
        os.environ.get("OPENROUTER_OUTPUT_USD_PER_MILLION"),
        max_output=4000,
    )
    sources = Sources(args.corpus)
    if {key: sources.documents[key]["sha256"] for key in benchmark["source_hashes"]} != benchmark[
        "source_hashes"
    ]:
        raise ValueError("Benchmark/corpus hash mismatch")
    ledger_path = args.output / "experiment.json"
    ledger = {
        "mode": "live_openrouter_development",
        "model": model.name,
        "budget_usd": args.budget_usd,
        "accounted_cost_usd": 0,
        "pricing": {
            "input_usd_per_million": model.input_rate,
            "output_usd_per_million": model.output_rate,
        },
        "benchmark_version": benchmark["version"],
        "source_hashes": benchmark["source_hashes"],
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True)
        ),
        "attempts": [],
        "status": "running",
        "limitation": "Application-side reservations are estimates, not a provider billing guarantee. Semantic support requires review.",
    }
    write_json(ledger_path, ledger)
    for task_id in args.tasks:
        remaining = args.budget_usd - ledger["accounted_cost_usd"]
        if remaining <= 1e-9:
            ledger["status"] = "aggregate_budget_exhausted"
            break
        reservation = min(args.per_task_usd, remaining)
        attempt = {
            "task_id": task_id,
            "status": "pending",
            "reserved_usd": reservation,
            "accounted_cost_usd": reservation,
        }
        ledger["attempts"].append(attempt)
        ledger["accounted_cost_usd"] += reservation
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
        ledger["accounted_cost_usd"] += actual - reservation
        # Persist known settlement before postprocessing, which can independently fail.
        result_path = args.output / f"{task_id}.json"
        write_json(result_path, report)
        attempt.update(
            status=report["status"],
            accounted_cost_usd=actual,
            metrics=report["metrics"],
            stop_reason=report["stop_reason"],
            result_file=result_path.name,
        )
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
        if report["metrics"]["cost_uncertain"] or ledger["accounted_cost_usd"] > args.budget_usd:
            ledger["status"] = "stopped_for_billing_review"
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
