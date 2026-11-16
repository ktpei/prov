"""Versioned application-input receipts; integrity checks, not signed attestations."""

import hashlib
import json
from importlib.metadata import version

from provenance.context import project_messages, tool_result_chars

PROFILE = "trace-receipts-v1"
VERSION = "model-input-receipt-v1"
PROJECTION = "recent-whole-results-32k-v1"
ADAPTER = "openrouter-langchain-messages-v1"


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def bound_tools(schemas):
    return [
        {
            "type": "function",
            "function": {key: schema[key] for key in ("name", "description", "parameters")},
        }
        for schema in schemas
    ]


def policy_identity(instructions, schemas, config):
    return {
        "adapter_version": ADAPTER,
        "projection_version": PROJECTION,
        "instructions_sha256": digest(instructions),
        "tool_schema_sha256": digest(schemas),
        "bound_tools_sha256": digest(bound_tools(schemas)),
        "workflow_version": "none",
        "answer_version": "legacy-v1",
        "evidence_version": "legacy_read_fragments",
        "config": config,
        "dependencies": {name: version(name) for name in ("langchain-core", "langchain-openai")},
    }


def make_receipt(
    history,
    projected,
    mapped,
    *,
    instructions,
    schemas,
    config,
    run_id,
    attempt_id,
    timeout,
    final_only,
):
    """Capture exactly the mapped objects used by the adapter, without credentials."""
    retained, omitted, fragments = [], [], []
    calls = {}
    if len(history) != len(projected):
        raise ValueError("Projection changed message inventory")
    for original, visible in zip(history, projected, strict=True):
        if original.get("type") == "function_call":
            identifier = original.get("call_id")
            if not isinstance(identifier, str) or identifier in calls:
                raise ValueError("Duplicate or invalid tool call identity")
            calls[identifier] = original.get("name")
        if original.get("type") != "function_call_output":
            continue
        identifier = original.get("call_id")
        if identifier not in calls or identifier in retained or identifier in omitted:
            raise ValueError("Unmatched or duplicate tool output")
        kept = original == visible
        (retained if kept else omitted).append(identifier)
        if not kept or calls[identifier] != "read_source":
            continue
        try:
            result = json.loads(original["output"])
        except (ValueError, TypeError):
            continue
        if not isinstance(result, dict) or "error" in result or not result.get("lines"):
            continue
        fragments.append(
            {
                "call_id": identifier,
                "result_sha256": digest(result),
                "source_id": result["id"],
                "locator": result["locator"],
                "lines": result["lines"],
            }
        )
    options = {"timeout": timeout}
    if final_only and schemas:
        options["tool_choice"] = "none"
    request = {
        "boundary": "langchain-application-messages-not-wire-bytes",
        "messages": [message.model_dump(mode="json") for message in mapped],
        "tools": bound_tools(schemas),
        "options": options,
        "config": config,
    }
    receipt = {
        "receipt_version": VERSION,
        "run_id": run_id,
        "attempt_id": attempt_id,
        "adapter_version": ADAPTER,
        "projection_version": PROJECTION,
        "instructions": instructions,
        "tool_schemas": schemas,
        "instructions_sha256": digest(instructions),
        "tool_schema_sha256": digest(schemas),
        "workflow_sha256": digest(None),
        "policy_sha256": digest(policy_identity(instructions, schemas, config)),
        "canonical_history": history,
        "canonical_history_sha256": digest(history),
        "projected_messages": projected,
        "projected_messages_sha256": digest(projected),
        "request": request,
        "request_sha256": digest(request),
        "retained_call_ids": retained,
        "omitted_call_ids": omitted,
        "evidence_inventory_kind": "legacy_read_fragments",
        "evidence_ids": [],
        "legacy_read_fragments": fragments,
        "input_characters": len(canonical(request)),
        "input_bytes": len(canonical(request).encode()),
        "tool_result_characters": tool_result_chars(projected),
        "final_only": final_only,
    }
    return json.loads(canonical(receipt))


def verify_receipt(receipt):
    """Rebuild the entire receipt, including mapping and retention decisions."""
    from provenance.langchain_model import chat_messages

    projected = project_messages(receipt["canonical_history"])
    expected = make_receipt(
        receipt["canonical_history"],
        projected,
        chat_messages(projected, instructions=receipt["instructions"]),
        instructions=receipt["instructions"],
        schemas=receipt["tool_schemas"],
        config=receipt["request"]["config"],
        run_id=receipt["run_id"],
        attempt_id=receipt["attempt_id"],
        timeout=receipt["request"]["options"]["timeout"],
        final_only=receipt["final_only"],
    )
    if canonical(expected) != canonical(receipt):
        raise ValueError("Model input receipt does not reconstruct")


def verify_report_receipts(report):
    """Bind reconstructable receipts to canonical model events and run identity."""
    events = report["events"]
    if (
        not isinstance(events, list)
        or len(events) < 3
        or not all(isinstance(e, dict) for e in events)
    ):
        raise ValueError("Missing complete receipt event trace")
    first = events[0]
    policy = first.get("receipt_policy")
    if report.get("runtime_profile") != PROFILE or not policy:
        raise ValueError("Report has no receipt profile")
    if (
        first.get("event") != "run_started"
        or events[-1].get("event") != "run_finished"
        or events[-1].get("status") != report.get("status")
        or first.get("runtime_profile") != PROFILE
        or first.get("checkpoint_version") != "research-checkpoint-v3"
        or first.get("question") != report.get("question")
        or first.get("mode") != report.get("mode")
    ):
        raise ValueError("Receipt trace boundaries differ")
    if (
        policy != policy_identity(first["instructions"], first["tools"], policy["config"])
        or policy["config"]["model"] != first["model"]
    ):
        raise ValueError("Receipt run policy differs")
    pending = None
    receipts = 0
    attempts, returned, responses = 0, set(), set()
    tool_outputs = {}
    history = [{"role": "user", "content": first["question"]}]
    for event in events:
        kind = event["event"]
        if kind in {"tool_result", "tool_call_skipped"}:
            identifier = event.get("call_id") if kind == "tool_result" else event["call"]["call_id"]
            tool_outputs[identifier] = event["result"]
            history.append(
                {
                    "type": "function_call_output",
                    "call_id": identifier,
                    "output": json.dumps(event["result"]),
                }
            )
        if kind == "controller_message":
            history.append(event["message"])
        if kind == "model_request":
            if pending is not None:
                raise ValueError("Model attempt lacks completion event")
            pending = {"event": event, "receipt": None, "dispatched": False}
            attempts += 1
            if event["number"] != attempts:
                raise ValueError("Model attempt sequence differs")
            if event["input"] != history:
                raise ValueError("Canonical model history is discontinuous")
        elif kind == "model_input_receipt":
            if pending is None or pending["receipt"] is not None:
                raise ValueError("Unexpected model receipt")
            receipt = event["receipt"]
            verify_receipt(receipt)
            request = pending["event"]
            if (
                receipt["run_id"] != report["run_id"]
                or receipt["attempt_id"] != request["number"]
                or receipt["canonical_history"] != request["input"]
                or receipt["final_only"] != request["final_only"]
                or receipt["instructions_sha256"] != policy["instructions_sha256"]
                or receipt["tool_schema_sha256"] != policy["tool_schema_sha256"]
                or receipt["request"]["config"] != policy["config"]
                or receipt["policy_sha256"] != digest(policy)
            ):
                raise ValueError("Receipt differs from run request or policy")
            for message in receipt["canonical_history"]:
                if message.get("type") == "function_call_output":
                    if (
                        message["call_id"] not in tool_outputs
                        or json.loads(message["output"]) != tool_outputs[message["call_id"]]
                    ):
                        raise ValueError("Receipt history differs from tool delivery")
            pending["receipt"] = receipt
            receipts += 1
        elif kind == "model_dispatch_started":
            if pending is None or pending["receipt"] is None or pending["dispatched"]:
                raise ValueError("Dispatch lacks unique receipt")
            if event["attempt_id"] != pending["event"]["number"]:
                raise ValueError("Dispatch attempt differs")
            pending["dispatched"] = True
        elif kind == "model_attempt_finished":
            if pending is None or event["attempt_id"] != pending["event"]["number"]:
                raise ValueError("Completion attempt differs")
            if event["returned"] and not pending["dispatched"]:
                raise ValueError("Returned attempt was never dispatched")
            if (
                event["receipt_created"] != (pending["receipt"] is not None)
                or event["dispatched"] != pending["dispatched"]
            ):
                raise ValueError("Attempt receipt/dispatch inventory differs")
            if event["returned"]:
                returned.add(event["attempt_id"])
            pending = None
        elif kind == "model_response":
            if event["number"] not in returned or event["number"] in responses:
                raise ValueError("Unexpected model response")
            responses.add(event["number"])
            history.extend(event["response"]["output"])
    if pending is not None:
        raise ValueError("Incomplete model attempt trace")
    if attempts != report["metrics"]["model_calls"] or returned != responses:
        raise ValueError("Report model attempt inventory differs")
    return {
        "receipts": receipts,
        "validation": "Application request integrity; not semantic support",
    }
