"""Run from the repository root: python3 -m provenance demo."""

import argparse
import json
import os
import sys
from pathlib import Path

from provenance.agent import Limits, Trace, run
from provenance.evaluation import grade, load_tasks, validate_dataset
from provenance.ingestion import ingest_packet
from provenance.model import OpenAIModel, ReplayModel
from provenance.openrouter import OpenRouterModel
from provenance.sources import Sources

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description="Read-only finance agent foundation")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Scripted offline plumbing demo; no model inference")
    demo.add_argument("--runtime", choices=["custom", "langgraph"], default="custom")
    demo.add_argument("--log-dir", type=Path, help="Explicitly allow writing run logs here")
    live = commands.add_parser("run", help="Opt-in live model run, with corpus or Exa retrieval")
    target = live.add_mutually_exclusive_group(required=True)
    target.add_argument("--question")
    target.add_argument(
        "--task", help="Development task ID; heldout execution is intentionally unavailable"
    )
    live.add_argument(
        "--live", action="store_true", help="Required acknowledgement of paid API use"
    )
    live.add_argument("--provider", choices=["openrouter", "openai"], default="openrouter")
    live.add_argument("--runtime", choices=["custom", "langgraph"], default="langgraph")
    live.add_argument("--web", action="store_true", help="Enable paid Exa search/contents")
    live.add_argument("--budget-usd", type=float, required=True)
    live.add_argument("--max-model-calls", type=int, default=8)
    live.add_argument("--max-tool-calls", type=int, default=10)
    live.add_argument("--timeout-seconds", type=float, default=90)
    live.add_argument("--log-dir", type=Path, help="Explicitly allow writing run logs here")
    ingest = commands.add_parser(
        "ingest", help="Build an immutable source packet from page-text JSON"
    )
    ingest.add_argument("--input", type=Path, required=True)
    ingest.add_argument("--output", type=Path, required=True)
    live.add_argument("--corpus", type=Path, default=ROOT / "data/corpus")
    commands.add_parser("validate", help="Validate evaluation dataset and source hashes")
    grading = commands.add_parser("grade", help="Mechanical checks on an existing dev run")
    grading.add_argument("--task", required=True)
    grading.add_argument("--result", type=Path, required=True)
    grading.add_argument("--allow-heldout", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "ingest":
            print(json.dumps(ingest_packet(args.input, args.output), indent=2))
            return 0
        if args.command == "validate":
            print(json.dumps(validate_dataset(ROOT), indent=2))
            return 0
        if args.command == "grade":
            tasks = load_tasks(ROOT / "eval/tasks.json")
            task = next((task for task in tasks if task["id"] == args.task), None)
            if task is None:
                raise ValueError("Unknown task ID")
            if task["split"] == "heldout" and not args.allow_heldout:
                raise ValueError(
                    "Heldout grading needs --allow-heldout; do not use it for development"
                )
            result = grade(task, json.loads(args.result.read_text()))
            print(json.dumps(result, indent=2))
            return 0 if result["mechanical_checks_passed"] else 1
        if args.command == "demo":
            fixture = json.loads((ROOT / "tests/fixtures/demo.json").read_text())
            question, model = fixture["question"], ReplayModel(fixture["responses"])
            sources, limits = Sources(ROOT / "data/corpus"), Limits()
        else:
            if not args.live:
                raise ValueError(
                    "Live API calls require --live; use 'demo' for offline verification"
                )
            if args.task and args.corpus != ROOT / "data/corpus":
                raise ValueError("Fixed-corpus evaluation tasks require the benchmark corpus")
            if args.task and args.web:
                raise ValueError("Fixed-corpus evaluation tasks cannot use --web")
            limits = Limits(
                args.max_model_calls,
                args.max_tool_calls,
                args.timeout_seconds,
                budget_usd=args.budget_usd,
            )
            prefix = "OPENROUTER" if args.provider == "openrouter" else "OPENAI"
            adapter = OpenRouterModel if args.provider == "openrouter" else OpenAIModel
            model = adapter(
                os.environ.get(f"{prefix}_API_KEY"),
                os.environ.get(f"{prefix}_MODEL"),
                os.environ.get(f"{prefix}_INPUT_USD_PER_MILLION"),
                os.environ.get(f"{prefix}_OUTPUT_USD_PER_MILLION"),
            )
            question = args.question
            if args.task:
                task = next(
                    (
                        task
                        for task in load_tasks(ROOT / "eval/tasks.json")
                        if task["id"] == args.task and task["split"] == "dev"
                    ),
                    None,
                )
                if task is None:
                    raise ValueError("Unknown development task (heldout tasks cannot be run here)")
                question = task["question"]  # Never pass expected answers or rubrics to the model.
            if not question.strip() or len(question) > 4000:
                raise ValueError("Question must contain 1–4000 characters")
            exa_key = os.environ.get("EXA_API_KEY") if args.web else None
            if args.web and not exa_key:
                raise ValueError("--web requires EXA_API_KEY")
            sources = Sources(
                args.corpus, exa_key=exa_key, exa_cap=os.environ.get("EXA_MAX_REQUEST_USD")
            )
            if args.task:
                sources.documents = {
                    key: source
                    for key, source in sources.documents.items()
                    if key in task["source_ids"]
                }
        report = run(question, model, sources, limits, Trace(args.log_dir), runtime=args.runtime)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if report["status"] == "completed" else 1
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(f"Configuration/data error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
