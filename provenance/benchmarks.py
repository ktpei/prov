"""Reproducible external benchmark preparation and offline answer-only scoring.

Prepared evaluator files contain gold data. Only inputs.json may reach a model.
No command in this module calls a model, downloads data, or executes gold programs.
"""

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

VERSION = "external-finance-v1"
LEGACY_SCORER_VERSION = "external-answer-only-v1"
SCORER_VERSION = "external-answer-only-v2"
PARTITION_V1 = "sha256(seed,document_or_id)-mod5-v1"
PARTITION_V2 = "sha256(seed,report_or_id)-mod5-v2"
CONDITIONS = {
    "fineval": {"model_only"},
    "finqa": {"supplied_context"},
    "tatqa": {"supplied_context"},
    "convfinqa": {"reference_history", "agent_history"},
    "financebench": {"evidence_supplied", "full_agent"},
}


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def model_input(task, condition):
    """Allowlist projection; no reference or arbitrary metadata reaches the agent."""
    dataset = task["dataset"]
    if condition not in CONDITIONS.get(dataset, set()):
        raise ValueError("Unsupported dataset/condition combination")
    payload = {"id": task["id"], "question": task["question"], "condition": condition}
    if dataset == "fineval":
        payload["context"] = {}
        payload["output_contract"] = 'Return only JSON {"answer": "A"} with one choice letter.'
    elif dataset == "finqa":
        payload["context"] = {
            key: task["context"][key] for key in ("pre_text", "post_text", "table")
        }
        payload["output_contract"] = (
            'Return only JSON {"answer": number_or_yes_no}. Use the numerical result in '
            "FinQA execution-result convention (percentage calculations may produce ratios); "
            "no unit suffix or explanatory text in answer. This is an answer-only adaptation."
        )
    elif dataset == "tatqa":
        payload["context"] = {
            "table": task["context"]["table"],
            "paragraphs": [
                {key: paragraph[key] for key in ("uid", "order", "text")}
                for paragraph in task["context"]["paragraphs"]
            ],
        }
        payload["output_contract"] = (
            'Return only JSON {"answer": string_or_number_or_string_list, '
            '"scale": ""}. Scale must be "", "thousand", "million", "billion", or "percent".'
        )
    elif dataset == "convfinqa":
        from provenance.table_conversation_adapters import conversation_input

        payload = conversation_input(
            task, 0, condition=condition, history=[] if condition == "agent_history" else None
        )
        payload["output_contract"] = (
            'Return only JSON {"answer": number_or_yes_no} in execution-result scale.'
        )
        payload["conversation_turn_count"] = len(task["reference"]["turns"])
    else:
        payload["context"] = {}
        if condition == "evidence_supplied":
            payload["context"]["evidence"] = [
                {key: entry[key] for key in ("doc_name", "evidence_page_num", "evidence_text")}
                for entry in task["reference"]["evidence"]
            ]
        else:
            payload["context"]["doc_name"] = task["metadata"]["doc_name"]
        payload["output_contract"] = (
            "Answer the question with cited supporting evidence. Evidence page numbers are "
            "zero-indexed. Full-agent mode requires a separately verified document corpus."
        )
    return payload


def partition_group(task, method=PARTITION_V2):
    """Keep a document together; related suites still require a cross-suite overlap audit."""
    metadata = task["metadata"]
    document = metadata.get("filename") or metadata.get("doc_name")
    if document and task["dataset"] in {"finqa", "convfinqa"} and method == PARTITION_V2:
        # Released FinQA filenames identify pages, not entire company reports.
        document = re.sub(r"/page_[0-9]+\.pdf$", "", str(document))
    return str(document) if document else task["id"]


def prepare(
    tasks, *, source, count, seed, condition, partition_method=PARTITION_V2, development_groups=()
):
    if not isinstance(development_groups, (list, tuple)) or any(
        not isinstance(group, str) or not group for group in development_groups
    ):
        raise ValueError("Development exposure groups must be nonempty strings")
    if partition_method == PARTITION_V1 and development_groups:
        raise ValueError("Legacy partitions cannot introduce exposure overrides")
    if partition_method not in {PARTITION_V1, PARTITION_V2}:
        raise ValueError("Unsupported partition method")
    if not tasks or type(count) is not int or count <= 0:
        raise ValueError("Nonempty tasks and positive integer count required")
    if type(seed) is not int:
        raise ValueError("Seed must be an integer")
    for key in ("url", "revision", "sha256", "license", "source_split", "subset", "dataset"):
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise ValueError(f"Source manifest requires {key}")
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", source["revision"]):
        raise ValueError("Pin an immutable upstream commit revision")
    if not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
        raise ValueError("Source sha256 must identify exact downloaded bytes")
    ids = [task["id"] for task in tasks]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate task IDs")
    if any(
        task[key] != source[key] for task in tasks for key in ("dataset", "subset", "source_split")
    ):
        raise ValueError("Mixed datasets, subsets, or source splits")
    # Hash groups, not questions: no shared document in internal dev/final partitions.
    assignments = {
        task["id"]: (
            "internal_final"
            if partition_group(task, partition_method) not in development_groups
            and int(canonical_hash([seed, partition_group(task, partition_method)])[:8], 16) % 5
            == 0
            else "dev"
        )
        for task in tasks
    }
    eligible = [task for task in tasks if assignments[task["id"]] == "dev"]
    eligible.sort(key=lambda task: canonical_hash([seed, task["id"]]))
    if count > len(eligible):
        raise ValueError(f"Requested {count} development tasks; only {len(eligible)} eligible")
    selected = eligible[:count]
    inputs = [model_input(task, condition) for task in selected]
    manifest = {
        "version": VERSION,
        "source": source,
        "seed": seed,
        "condition": condition,
        "partition_method": partition_method,
        "scorer_version": SCORER_VERSION,
        "partitions": assignments,
        "selected_ids": [task["id"] for task in selected],
        "inputs_sha256": canonical_hash(inputs),
        "tasks_sha256": canonical_hash(selected),
        "limitations": [
            "Internal development/final partition of public data, not a secret holdout.",
            "No model quality measured by preparation or synthetic scorer checks.",
            "FinQA answer-only uses final five-decimal rounding and no implicit percent conversion.",
            "Public CFA scenarios may overlap across questions; no scenario-disjoint claim is made.",
            "Cross-suite FinQA/ConvFinQA overlap requires a separate document audit.",
            "FinanceBench strict success requires calibrated semantic and evidence review.",
        ],
    }
    if partition_method == PARTITION_V2:
        manifest["development_groups"] = sorted(set(development_groups))
    return {"manifest": manifest, "tasks": selected, "inputs": inputs}


def decimal_answer(value):
    if type(value) not in (int, float, str):
        raise ValueError("Answer must be a finite scalar")
    if isinstance(value, str) and not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", value.strip()):
        raise ValueError("Answer must be a plain decimal without units or explanation")
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal answer") from exc
    if not number.is_finite():
        raise ValueError("Nonfinite answer")
    return number


def score_answer(task, prediction, *, scorer_version=SCORER_VERSION):
    """Conservative adaptation, never official program accuracy or semantic grading."""
    dataset = task["dataset"]
    result = {
        "id": task["id"],
        "scorer_version": scorer_version,
        "metric": task["reference"]["metric"],
        "passed": False,
        "status": "invalid_output",
    }
    if task["reference"].get("requires_review"):
        result.update(passed=None, status="reference_conflict_requires_review")
        return result
    if dataset == "tatqa":
        from provenance.official_metrics import score_tatqa

        official = score_tatqa(task["reference"], prediction)
        return {**result, **official, "passed": official["exact_match"] == 1.0}
    if dataset == "convfinqa":
        from provenance.conversation_eval import score_conversation

        return {**result, **score_conversation(task, prediction)}
    if dataset == "financebench":
        if (
            not isinstance(prediction, dict)
            or not isinstance(prediction.get("answer_text"), str)
            or not prediction["answer_text"].strip()
        ):
            return result
        result.update(passed=None, status="requires_semantic_review")
        return result
    if not isinstance(prediction, dict) or set(prediction) != {"answer"}:
        return result
    value = prediction["answer"]
    if dataset == "fineval":
        if not isinstance(value, str) or not re.fullmatch(r"[A-Z]", value.strip()):
            return result
        result.update(status="scored", passed=value.strip() == task["reference"]["answer"])
    elif dataset == "finqa":
        expected = task["reference"]["exe_ans"]
        if isinstance(expected, str) and expected.lower() in {"yes", "no"}:
            if not isinstance(value, str) or value.strip().lower() not in {"yes", "no"}:
                return result
            passed = value.strip().lower() == expected.lower()
        else:
            try:
                actual_number = decimal_answer(value)
                expected_number = decimal_answer(expected)
                # Match upstream final scalar rounding; no program execution is claimed.
                actual_float, expected_float = float(actual_number), float(expected_number)
                if not all(math.isfinite(n) for n in (actual_float, expected_float)):
                    return result
                passed = round(actual_float, 5) == expected_float
            except ValueError:
                return result
        result.update(status="scored", passed=passed)
    else:
        raise ValueError("Unsupported scorer")
    return result


def score_run(bundle, submission):
    """Keep every selected task in denominator; reject foreign/duplicate result IDs."""
    manifest, tasks = bundle["manifest"], bundle["tasks"]
    scorer_version = manifest.get("scorer_version", LEGACY_SCORER_VERSION)
    if scorer_version not in {LEGACY_SCORER_VERSION, SCORER_VERSION}:
        raise ValueError("Unsupported scorer version")
    if manifest.get("version") != VERSION:
        raise ValueError("Unsupported prepared manifest version")
    checked = prepare(
        tasks,
        source=manifest["source"],
        count=len(tasks),
        seed=manifest["seed"],
        condition=manifest["condition"],
        partition_method=manifest["partition_method"],
        development_groups=manifest.get("development_groups", []),
    )
    if checked["manifest"]["selected_ids"] != manifest["selected_ids"] or any(
        manifest["partitions"].get(task["id"]) != "dev" for task in tasks
    ):
        raise ValueError("Prepared development partition mismatch")
    if canonical_hash(tasks) != manifest["tasks_sha256"]:
        raise ValueError("Prepared task hash mismatch")
    if [task["id"] for task in tasks] != manifest["selected_ids"]:
        raise ValueError("Prepared selection mismatch")
    if canonical_hash(bundle["inputs"]) != manifest["inputs_sha256"]:
        raise ValueError("Prepared input hash mismatch")
    if bundle["inputs"] != [model_input(task, manifest["condition"]) for task in tasks]:
        raise ValueError("Prepared inputs differ from allowed projection")
    if not isinstance(submission, dict) or submission.get("prepared_sha256") != canonical_hash(
        manifest
    ):
        raise ValueError("Prediction submission does not match prepared manifest")
    predictions = submission.get("predictions")
    if not isinstance(predictions, list):
        raise ValueError("Prediction submission requires a predictions list")
    by_id = {}
    for row in predictions:
        if row["id"] in by_id or row["id"] not in manifest["selected_ids"]:
            raise ValueError("Duplicate or unknown prediction ID")
        by_id[row["id"]] = row
    rows = []
    for task in tasks:
        prediction = by_id.get(task["id"])
        if task["reference"].get("requires_review") and scorer_version != LEGACY_SCORER_VERSION:
            rows.append(score_answer(task, None, scorer_version=scorer_version))
        elif task["dataset"] == "convfinqa" and prediction is not None:
            graded = score_answer(task, prediction.get("output"), scorer_version=scorer_version)
            graded["answer_sequence_passed"] = graded["passed"]
            graded["completion_status"] = prediction.get("status")
            if prediction.get("status") != "completed":
                graded["passed"] = False
                if graded["answer_sequence_passed"]:
                    graded["status"] = "conversation_status_inconsistent"
            rows.append(graded)
        elif prediction is None or prediction.get("status") != "completed":
            rows.append({"id": task["id"], "passed": False, "status": "missing_or_incomplete"})
        else:
            rows.append(score_answer(task, prediction.get("output"), scorer_version=scorer_version))
    pending = sum(row["passed"] is None for row in rows)
    report = {
        "version": VERSION,
        "scorer_version": scorer_version,
        "dataset": manifest["source"]["dataset"],
        "condition": manifest["condition"],
        "prepared_sha256": canonical_hash(manifest),
        "source": manifest["source"],
        "selected_ids": manifest["selected_ids"],
        "inputs_sha256": manifest["inputs_sha256"],
        "submission_sha256": canonical_hash(submission),
        "execution_provenance": "identity_bound_but_execution_not_independently_verified",
        "selected_count": len(tasks),
        "passed_count": sum(row["passed"] is True for row in rows),
        "pending_review_count": pending,
        "accuracy": (
            None
            if pending or manifest["source"]["dataset"] == "financebench"
            else sum(row["passed"] is True for row in rows) / len(tasks)
        ),
        "statuses": dict(Counter(row["status"] for row in rows)),
        "tasks": rows,
        "limitations": manifest["limitations"],
    }

    if manifest["source"]["dataset"] == "tatqa":
        report["official_metrics"] = {
            key: None if pending else sum(row.get(key, 0.0) for row in rows) / len(tasks)
            for key in ("exact_match", "f1", "scale_accuracy")
        }
    elif manifest["source"]["dataset"] == "convfinqa":
        turn_count = sum(len(task["reference"]["turns"]) for task in tasks)
        turn_passed = sum(row.get("turn_passed_count", 0) for row in rows)
        report["conversation_metrics"] = {
            "conversation_count": len(tasks),
            "completed_conversation_count": sum(
                row.get("completion_status") == "completed" for row in rows
            ),
            "whole_conversation_accuracy": report["accuracy"],
            "turn_count": turn_count,
            "turn_passed_count": turn_passed,
            "turn_accuracy": turn_passed / turn_count,
        }
    return report


def load_bundle(directory):
    return {
        key: json.loads((Path(directory) / f"{key}.json").read_text())
        for key in ("manifest", "tasks", "inputs")
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("prepare")
    build.add_argument("--source-manifest", type=Path, required=True)
    build.add_argument("--condition", required=True)
    build.add_argument("--input", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--count", type=int, required=True)
    build.add_argument("--seed", type=int, default=20261116)
    score = commands.add_parser("score")
    score.add_argument("--prepared", type=Path, required=True)
    score.add_argument("--predictions", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        from provenance.benchmark_adapters import adapt_records
        from provenance.benchmark_data import read_records
        from provenance.reference_issues import apply_reference_issues

        source = json.loads(args.source_manifest.read_text())
        raw = args.input.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError("Input bytes differ from pinned source manifest")
        records = read_records(args.input)
        tasks = adapt_records(
            source["dataset"], records, subset=source["subset"], source_split=source["source_split"]
        )
        registry = json.loads(
            (Path(__file__).resolve().parent.parent / "eval/reference-issues.json").read_text()
        )
        tasks, _ = apply_reference_issues(tasks, source, registry)
        exposures = json.loads(
            (Path(__file__).resolve().parent.parent / "eval/development-exposures.json").read_text()
        )
        if exposures.get("version") != "finance-development-exposures-v1":
            raise ValueError("Unknown development exposure registry")
        bundle = prepare(
            tasks,
            source=source,
            count=args.count,
            seed=args.seed,
            condition=args.condition,
            development_groups=[entry["group"] for entry in exposures["groups"]],
        )
        bundle["manifest"]["development_exposures_sha256"] = canonical_hash(exposures)
        bundle["manifest"]["reference_registry_sha256"] = canonical_hash(registry)
        bundle["manifest"]["applied_reference_issues"] = sorted(
            {
                issue
                for task in bundle["tasks"]
                for issue in task["reference"].get("reference_issues", [])
            }
        )
        args.output.mkdir(parents=True, exist_ok=False)
        for key, value in bundle.items():
            (args.output / f"{key}.json").write_text(
                json.dumps(value, indent=2, allow_nan=False) + "\n"
            )
        print(
            json.dumps(
                {"prepared": len(bundle["tasks"]), "output": str(args.output), "model_calls": 0}
            )
        )
    else:
        report = score_run(load_bundle(args.prepared), json.loads(args.predictions.read_text()))
        with args.output.open("x") as handle:
            handle.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
        print(
            json.dumps(
                {key: value for key, value in report.items() if key not in {"tasks", "limitations"}}
            )
        )


if __name__ == "__main__":
    main()
