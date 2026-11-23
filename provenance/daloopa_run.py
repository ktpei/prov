"""Plan quick/full Daloopa runs; paid execution requires --live and explicit source access."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path
from urllib.parse import urlparse

from provenance.agent import Limits, Trace
from provenance.benchmarks import canonical_hash
from provenance.controls import positive
from provenance.daloopa import PROTECTED, ROOT, load, validate
from provenance.daloopa_score import REVIEW_FIELDS, review_identity, score
from provenance.document_navigation import (
    NAVIGATION_INSTRUCTIONS,
    NAVIGATION_TOOLS,
    NavigableExaSources,
)
from provenance.exa_sources import EXA_INSTRUCTIONS, EXA_TOOL_SCHEMAS, ExaSources
from provenance.experiment import write_json
from provenance.graph import run_graph
from provenance.langchain_model import OpenRouterModel
from provenance.model import INSTRUCTIONS
from provenance.sources import TOOL_SCHEMAS

LIMITS = Limits(
    max_model_calls=6,
    max_tool_calls=8,
    timeout_seconds=90,
    request_timeout_seconds=30,
    budget_usd=0.05,
)
MAX_OUTPUT = 1800
BLOCKED_DOMAINS = (
    "daloopa.com",
    "huggingface.co",
    "github.com",
    "github.io",
    "chatgpt.com",
    "claude.ai",
    "grok.com",
    "perplexity.ai",
    "gemini.google.com",
)


def forbidden(metadata):
    host = (urlparse(metadata.get("url", "")).hostname or "").lower()
    if any(host == domain or host.endswith("." + domain) for domain in BLOCKED_DOMAINS):
        return True
    text = " ".join(str(metadata.get(k, "")) for k in ("company", "title", "url"))
    names = (
        list(PROTECTED)
        + list(PROTECTED.values())
        + ["Advanced Micro Devices", "Square Inc", "Square, Inc"]
    )
    return any(re.search(r"\b" + re.escape(name) + r"\b", text, re.I) for name in names)


class BenchmarkSources(ExaSources):
    def __init__(self, directory, **kwargs):
        # Sources eagerly opens text files: inspect only manifest metadata first.
        manifest = json.loads((Path(directory) / "sources.json").read_text())
        if any(forbidden(source) for source in manifest["sources"]):
            raise ValueError("Corpus contains reserved issuers or benchmark-answer sources")
        super().__init__(directory, **kwargs)

    def search(self, query, timeout, objective=None):
        if forbidden({"title": query}) or forbidden({"title": objective or ""}):
            raise ValueError("Reserved issuer queries are unavailable in development")
        result = super().search(query, timeout, objective)
        allowed = []
        for hit in result["results"]:
            source_id = hit.get("source_id", hit.get("id"))
            metadata = self.documents.get(source_id, hit)
            if not forbidden(metadata):
                allowed.append(hit)
            elif source_id in self.documents:
                del self.documents[source_id]
        return {**result, "results": allowed}

    def read(self, source_id, start, end, timeout):
        if source_id in self.documents and forbidden(self.documents[source_id]):
            raise ValueError("Reserved issuer or benchmark-answer source")
        return super().read(source_id, start, end, timeout)


class NavigableBenchmarkSources(BenchmarkSources, NavigableExaSources):
    def _document(self, source_id, timeout):
        if source_id in self.documents and forbidden(self.documents[source_id]):
            raise ValueError("Reserved issuer or benchmark-answer source")
        return super()._document(source_id, timeout)


def plan(bundle, profile):
    validate(bundle)
    ids = bundle["manifest"][f"{profile}_ids"]
    tasks = {task["id"]: task for task in bundle["tasks"]}
    return {
        "profile": profile,
        "selected": len(ids),
        "full_inventory": len(tasks),
        "dispositions": dict(Counter(tasks[key]["status"] for key in ids)),
        "selected_ids": ids,
        "limits": asdict(LIMITS),
        "max_output_tokens": MAX_OUTPUT,
        "model_calls": 0,
    }


def run_benchmark(
    bundle,
    model,
    output,
    *,
    profile="quick",
    corpus=None,
    web_key=None,
    web_cap=None,
    budget_usd=0.5,
    per_task_usd=0.05,
    execute=run_graph,
    navigation="baseline",
):
    if navigation not in {"baseline", "document-v1"}:
        raise ValueError("Unknown navigation policy")
    if navigation != "baseline" and not web_key:
        raise ValueError("Document navigation comparison requires web retrieval")
    selection = plan(bundle, profile)
    if budget_usd is not None:
        positive(budget_usd, "aggregate budget")
        positive(per_task_usd, "per-task budget")
    elif per_task_usd is not None:
        raise ValueError("Uncapped runs require per_task_usd=None")
    if web_key:
        positive(web_cap, "Exa request cap")
    if not corpus and not web_key:
        raise ValueError("Supply an issuer corpus or enable Exa web retrieval")
    expected_instructions = EXA_INSTRUCTIONS if web_key else INSTRUCTIONS
    expected_tools = EXA_TOOL_SCHEMAS if web_key else TOOL_SCHEMAS
    if navigation == "document-v1":
        expected_instructions, expected_tools = NAVIGATION_INSTRUCTIONS, NAVIGATION_TOOLS
    if model.instructions != expected_instructions or model.tool_schemas != expected_tools:
        raise ValueError("Benchmark requires unchanged research instructions and search/read tools")
    if model.max_output != MAX_OUTPUT:
        raise ValueError("Quick and full use the same frozen output-token limit")
    # Validate existing corpus before making an output directory or issuing requests.
    if corpus:
        BenchmarkSources(corpus)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    if not corpus:
        corpus = output / "empty-corpus"
        corpus.mkdir()
        write_json(corpus / "sources.json", {"sources": []})
    manifest = bundle["manifest"]
    tasks = {task["id"]: task for task in bundle["tasks"]}
    inputs = {row["id"]: row for row in bundle["inputs"]}
    policy = {
        "navigation": navigation,
        "model": model.name,
        "limits": asdict(replace(LIMITS, budget_usd=per_task_usd)),
        "max_output_tokens": MAX_OUTPUT,
        "instructions_sha256": canonical_hash(model.instructions),
        "tool_schema_sha256": canonical_hash(model.tool_schemas),
        "source_access": "corpus_and_web" if web_key else "frozen_corpus",
        "corpus_manifest_sha256": hashlib.sha256(
            (Path(corpus) / "sources.json").read_bytes()
        ).hexdigest(),
        "exa_request_cap": web_cap if web_key else None,
        "implementation_sha256": {
            name: hashlib.sha256((ROOT / "provenance" / name).read_bytes()).hexdigest()
            for name in (
                "daloopa.py",
                "daloopa_score.py",
                "daloopa_run.py",
                "exa_sources.py",
                "document_navigation.py",
                "context.py",
                "graph.py",
                "model.py",
                "sources.py",
                "langchain_model.py",
            )
        },
    }
    ledger = {
        "prepared_sha256": canonical_hash(manifest),
        "profile": profile,
        "policy": policy,
        "policy_sha256": canonical_hash(policy),
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True)
        ),
        "mode": model.mode,
        "pricing": {"input": model.input_rate, "output": model.output_rate},
        "budget_usd": budget_usd,
        "accounted_cost_usd": 0,
        "status": "running",
        "records": [
            {
                "id": key,
                "status": "not_started"
                if tasks[key]["status"] != "reserved_issuer"
                else tasks[key]["status"],
            }
            for key in selection["selected_ids"]
        ],
    }
    ledger_path = output / "submission.json"
    write_json(ledger_path, ledger)
    review_rows = []
    for row in ledger["records"]:
        if row["status"] != "not_started":
            continue
        remaining = budget_usd - ledger["accounted_cost_usd"] if budget_usd is not None else None
        if remaining is not None and remaining <= 1e-12:
            ledger["status"] = "aggregate_budget_exhausted"
            break
        cap = min(per_task_usd, remaining) if remaining is not None else None
        source_class = (
            NavigableBenchmarkSources if navigation == "document-v1" else BenchmarkSources
        )
        sources = source_class(corpus, exa_key=web_key, exa_cap=web_cap)
        row.update(
            status="pending", reserved_usd=cap, accounted_cost_usd=cap or 0, cost_uncertain=True
        )
        ledger["accounted_cost_usd"] += cap or 0
        write_json(ledger_path, ledger)  # Crash-safe reservation BEFORE dispatch.
        print(json.dumps({"id": row["id"], "status": "starting"}), flush=True)
        prompt = json.dumps(inputs[row["id"]], ensure_ascii=False)
        report = execute(
            prompt,
            model,
            sources,
            replace(LIMITS, budget_usd=cap),
            Trace(output / "traces"),
            **({"runtime_profile": "trace-receipts-v1"} if web_key else {}),
        )
        actual = report["metrics"]["accounted_cost_usd"]
        ledger["accounted_cost_usd"] += actual - (cap or 0)
        evidence = {"documents": {key: sources.documents[key] for key in sources.seen}}
        record = {"report": report, "evidence": evidence}
        row.update(
            status=report["status"],
            accounted_cost_usd=actual,
            cost_uncertain=report["metrics"]["cost_uncertain"],
            **record,
        )
        write_json(output / (row["id"] + ".json"), record)
        write_json(ledger_path, ledger)
        if report["status"] == "completed":
            review_rows.append(
                {
                    **review_identity(tasks[row["id"]], row),
                    "reviewer": "",
                    "reviewer_kind": "human",
                    "notes": "",
                    **dict.fromkeys(REVIEW_FIELDS),
                }
            )
            write_json(output / "review-template.json", review_rows)
        write_json(output / "score.json", score(bundle, ledger))
        print(
            json.dumps({"id": row["id"], "status": row["status"], "cost_usd": actual}), flush=True
        )
        if row["cost_uncertain"] or (
            budget_usd is not None and ledger["accounted_cost_usd"] > budget_usd
        ):
            ledger["status"] = "stopped_for_billing_review"
            break
        if report.get("stop_reason") == "user_interrupted":
            ledger["status"] = "interrupted"
            break
    if ledger["status"] == "running":
        ledger["status"] = "finished"
    for row in ledger["records"]:
        if row["status"] == "not_started":
            row.update(status="skipped", reason=ledger["status"])
    write_json(ledger_path, ledger)
    write_json(output / "score.json", score(bundle, ledger))
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, default=Path("runs/benchmark-prepared/daloopa"))
    parser.add_argument("--profile", choices=("quick", "full"), default="quick")
    parser.add_argument("--navigation", choices=("baseline", "document-v1"), default="baseline")
    parser.add_argument("--live", action="store_true", help="Explicitly enable paid model calls")
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--web", action="store_true", help="Enable paid Exa search/contents")
    parser.add_argument("--output", type=Path)
    spending = parser.add_mutually_exclusive_group()
    spending.add_argument("--budget-usd", type=float)
    spending.add_argument("--no-spend-limit", action="store_true")
    parser.add_argument("--per-task-usd", type=float)
    args = parser.parse_args()
    bundle = load(args.prepared)
    if not args.live:
        print(
            json.dumps(
                {k: v for k, v in plan(bundle, args.profile).items() if k != "selected_ids"},
                indent=2,
            )
        )
        return
    if not args.output:
        parser.error("--live requires a new --output directory")
    if args.no_spend_limit and args.per_task_usd is not None:
        parser.error("--per-task-usd cannot accompany --no-spend-limit")
    web_key = os.environ.get("EXA_API_KEY") if args.web else None
    if args.web and not web_key:
        parser.error("--web requires EXA_API_KEY")
    web_cap = (
        positive(os.environ.get("EXA_MAX_REQUEST_USD", "0"), "EXA_MAX_REQUEST_USD")
        if args.web
        else None
    )
    model = OpenRouterModel(
        os.environ.get("OPENROUTER_API_KEY"),
        os.environ.get("OPENROUTER_MODEL"),
        os.environ.get("OPENROUTER_INPUT_USD_PER_MILLION"),
        os.environ.get("OPENROUTER_OUTPUT_USD_PER_MILLION"),
        max_output=MAX_OUTPUT,
        instructions=NAVIGATION_INSTRUCTIONS
        if args.navigation == "document-v1"
        else (EXA_INSTRUCTIONS if args.web else INSTRUCTIONS),
        tool_schemas=NAVIGATION_TOOLS
        if args.navigation == "document-v1"
        else (EXA_TOOL_SCHEMAS if args.web else TOOL_SCHEMAS),
    )
    ledger = run_benchmark(
        bundle,
        model,
        args.output,
        profile=args.profile,
        corpus=args.corpus,
        web_key=web_key,
        web_cap=web_cap,
        navigation=args.navigation,
        budget_usd=None
        if args.no_spend_limit
        else (args.budget_usd if args.budget_usd is not None else 0.5),
        per_task_usd=None
        if args.no_spend_limit
        else (args.per_task_usd if args.per_task_usd is not None else 0.05),
    )
    print(json.dumps({"status": ledger["status"], "cost_usd": ledger["accounted_cost_usd"]}))


if __name__ == "__main__":
    main()
