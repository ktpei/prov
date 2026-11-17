"""Bounded, single-attempt execution for prepared ConvFinQA conversations."""

import copy
import json
import math
import subprocess
import time
from pathlib import Path

from provenance.benchmark_run import INSTRUCTIONS, PROMPT_VERSION, parse_output
from provenance.benchmarks import canonical_hash, decimal_answer, score_run
from provenance.controls import Budget, LimitReached, deadline, positive
from provenance.experiment import write_json
from provenance.table_conversation_adapters import conversation_input
from provenance.transport import ProviderError


def _scalar_answer(parsed):
    if not isinstance(parsed, dict) or set(parsed) != {"answer"}:
        return None
    answer = parsed["answer"]
    if isinstance(answer, bool):
        return None
    if type(answer) in (int, float):
        return answer if math.isfinite(answer) else None
    if not isinstance(answer, str):
        return None
    answer = answer.strip()
    if answer.lower() in {"yes", "no"}:
        return answer.lower()
    try:
        if not math.isfinite(float(decimal_answer(answer))):
            return None
    except ValueError:
        return None
    return answer


def _safe_last_response(model):
    response = getattr(model, "last_response", None)
    if not isinstance(response, dict):
        return None
    safe = {
        key: copy.deepcopy(response[key])
        for key in ("content", "finish_reason", "usage")
        if key in response
    }
    try:
        canonical_hash(safe)
    except (TypeError, ValueError):
        return None
    return safe


def _turn_input(task, turn_index, condition, history, prepared_input):
    payload = conversation_input(
        task,
        turn_index,
        condition=condition,
        history=history if condition == "agent_history" else None,
    )
    payload["output_contract"] = prepared_input["output_contract"]
    payload["conversation_turn_count"] = prepared_input["conversation_turn_count"]
    return payload


def _skip_not_started(ledger, reason):
    for conversation in ledger["predictions"]:
        if conversation["status"] == "not_started":
            conversation.update(status="skipped", failure=reason)
        for turn in conversation["output"]["turns"]:
            if turn["status"] == "not_started":
                turn.update(status="skipped", failure=reason)


def run_conversations(
    bundle,
    model,
    output,
    *,
    budget_usd,
    per_task_usd,
    per_turn_usd=0.02,
    timeout=60,
):
    """Run every selected turn once, retaining durable per-request reservations."""
    budget_usd = positive(budget_usd, "aggregate budget")
    per_task_usd = positive(per_task_usd, "conversation budget")
    per_turn_usd = positive(per_turn_usd, "turn budget")
    timeout = positive(timeout, "timeout")
    manifest = bundle["manifest"]
    identity = canonical_hash(manifest)
    score_run(bundle, {"prepared_sha256": identity, "predictions": []})
    if manifest["source"]["dataset"] != "convfinqa":
        raise ValueError("Conversation runner requires a convfinqa bundle")
    if manifest["condition"] not in {"reference_history", "agent_history"}:
        raise ValueError("Unsupported ConvFinQA conversation condition")
    if (
        getattr(model, "instructions", None) != INSTRUCTIONS
        or getattr(model, "tool_schemas", None) != []
    ):
        raise ValueError("Runner requires benchmark instructions and no model tools")

    tasks = bundle["tasks"]
    prepared_inputs = bundle["inputs"]
    for task, prepared_input in zip(tasks, prepared_inputs, strict=True):
        first = _turn_input(task, 0, manifest["condition"], [], prepared_input)
        if first != prepared_input:
            raise ValueError("Prepared first input differs from conversation projection")

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    ledger = {
        "prepared_sha256": identity,
        "mode": model.mode,
        "model": model.name,
        "prompt_version": PROMPT_VERSION,
        "generation": {
            "max_output_tokens": getattr(model, "max_output", None),
            "temperature": 0,
            "max_retries": 0,
            "provider_routing": "OpenRouter default routing; no provider override",
        },
        "instructions": INSTRUCTIONS,
        "inputs_sha256": manifest["inputs_sha256"],
        "source": manifest["source"],
        "condition": manifest["condition"],
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True)
        ),
        "budget_usd": budget_usd,
        "per_task_usd": per_task_usd,
        "per_turn_usd": per_turn_usd,
        "timeout_seconds": timeout,
        "pricing": {
            "input_usd_per_million": model.input_rate,
            "output_usd_per_million": model.output_rate,
        },
        "accounted_cost_usd": 0,
        "status": "running",
        "predictions": [
            {
                "id": task["id"],
                "status": "not_started",
                "output": {
                    "turns": [
                        {"turn_index": index, "status": "not_started"}
                        for index in range(len(task["reference"]["turns"]))
                    ]
                },
            }
            for task in tasks
        ],
        "limitations": [
            "Application reservations estimate costs; they are not invoice totals.",
            "One attempt per turn; no automatic retry, repair, or resume.",
            "ConvFinQA scoring is an answer-only adaptation, not program accuracy.",
        ],
    }
    path = output / "submission.json"
    write_json(path, ledger)

    stop_batch = False
    for task, prepared_input, conversation in zip(
        tasks, prepared_inputs, ledger["predictions"], strict=True
    ):
        if task["reference"].get("requires_review"):
            conversation.update(
                status="reference_review_required",
                failure="Unresolved reference; no inference attempted",
            )
            for turn in conversation["output"]["turns"]:
                turn.update(
                    status="reference_review_required",
                    failure="Unresolved reference; no inference attempted",
                )
            write_json(path, ledger)
            continue

        history = []
        conversation_cost = 0.0
        conversation["status"] = "running"
        write_json(path, ledger)
        for turn_index, turn in enumerate(conversation["output"]["turns"]):
            remaining_global = budget_usd - ledger["accounted_cost_usd"]
            remaining_conversation = per_task_usd - conversation_cost
            if remaining_global <= 1e-12:
                ledger["status"] = "aggregate_budget_exhausted"
                conversation["status"] = "stopped"
                _skip_not_started(ledger, "aggregate_budget_exhausted")
                write_json(path, ledger)
                stop_batch = True
                break
            if remaining_conversation <= 1e-12:
                conversation["status"] = "conversation_budget_exhausted"
                for pending in conversation["output"]["turns"]:
                    if pending["status"] == "not_started":
                        pending.update(status="skipped", failure="conversation_budget_exhausted")
                write_json(path, ledger)
                break

            reservation = min(per_turn_usd, remaining_global, remaining_conversation)
            payload = _turn_input(task, turn_index, manifest["condition"], history, prepared_input)
            turn.update(
                status="pending",
                reserved_usd=reservation,
                accounted_cost_usd=reservation,
                input=payload,
                input_sha256=canonical_hash(payload),
            )
            ledger["accounted_cost_usd"] += reservation
            conversation_cost += reservation
            write_json(path, ledger)

            request_budget = Budget(reservation)
            started = time.monotonic()
            response = None
            request_error = None
            try:
                with deadline(timeout) as time_left:
                    response = model.step(
                        [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                        time_left(),
                        request_budget,
                    )
                turn["raw_response"] = response
            except (ProviderError, LimitReached) as exc:
                request_error = exc
                rejected = _safe_last_response(model)
                if rejected is not None:
                    turn["rejected_provider_response"] = rejected
            # Unexpected exceptions deliberately escape with the full pending reservation intact.

            accounted = (
                max(reservation, request_budget.charged)
                if request_budget.uncertain
                else request_budget.charged
            )
            turn.update(
                accounted_cost_usd=accounted,
                cost_uncertain=request_budget.uncertain,
                latency_seconds=time.monotonic() - started,
            )
            ledger["accounted_cost_usd"] += accounted - reservation
            conversation_cost += accounted - reservation
            write_json(path, ledger)

            if request_error is not None:
                turn.update(
                    status="failed",
                    failure=str(request_error),
                    parse_status="request_failed",
                )
            else:
                try:
                    parsed, parse_status = parse_output(response, structured=True)
                except ProviderError as exc:
                    turn.update(status="failed", failure=str(exc), parse_status="response_rejected")
                else:
                    answer = _scalar_answer(parsed) if parse_status == "parsed" else None
                    if answer is None:
                        turn.update(status="invalid_output", output=None, parse_status=parse_status)
                    else:
                        turn.update(
                            status="completed",
                            output={"answer": answer},
                            parse_status=parse_status,
                        )
                        history.append(answer)
            write_json(path, ledger)

            if request_budget.uncertain or ledger["accounted_cost_usd"] > budget_usd + 1e-12:
                ledger["status"] = "stopped_for_billing_review"
                conversation["status"] = "stopped"
                _skip_not_started(ledger, "stopped_for_billing_review")
                write_json(path, ledger)
                stop_batch = True
                break
            if manifest["condition"] == "agent_history" and turn["status"] != "completed":
                conversation["status"] = "failed"
                for pending in conversation["output"]["turns"]:
                    if pending["status"] == "not_started":
                        pending.update(
                            status="skipped_after_invalid_history",
                            failure="skipped_after_invalid_history",
                        )
                write_json(path, ledger)
                break

        if stop_batch:
            break
        statuses = [turn["status"] for turn in conversation["output"]["turns"]]
        if all(status == "completed" for status in statuses):
            conversation["status"] = "completed"
        elif conversation["status"] == "running":
            conversation["status"] = "failed"
        write_json(path, ledger)

    if ledger["status"] == "running":
        ledger["status"] = "finished"
    _skip_not_started(ledger, ledger["status"])
    write_json(path, ledger)
    write_json(output / "score.json", score_run(bundle, ledger))
    return ledger
