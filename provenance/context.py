"""Bound model-visible tool evidence without modifying canonical run history.

Only complete tool results are omitted. Call IDs, call/output pairs, user messages
and assistant messages remain intact. Durable traces and citation-read ledgers
remain the caller's responsibility and must receive the canonical history.
"""

import json

from provenance.controls import LimitReached


def tool_result_chars(messages):
    """Count serialized JSON output-string characters, including string escaping."""
    return sum(
        len(json.dumps(message["output"], ensure_ascii=False))
        for message in messages
        if message.get("type") == "function_call_output"
    )


def _omission(message):
    note = {
        "omitted_from_model_context": True,
        "note": "Full result remains in run history. Search or read_source again if needed.",
    }
    try:
        result = json.loads(message["output"])
    except (json.JSONDecodeError, TypeError):
        result = None
    if isinstance(result, dict):
        source_id = result.get("id", result.get("source_id"))
        if isinstance(source_id, str):
            note["source_id"] = source_id
        if isinstance(result.get("locator"), str):
            note["locator"] = result["locator"]
    return {**message, "output": json.dumps(note, ensure_ascii=False)}


def project_messages(messages, *, max_tool_result_chars=32_000):
    """Return a model projection retaining the newest search and read in full.

    Older searches are navigation history and are always omitted. Additional old
    reads/results are retained newest-first when they fit. If even the omission
    notes plus newest search/read cannot fit, stop explicitly before a paid call;
    an oversized evidence result is never clipped into an apparently exact quote.
    """
    if type(max_tool_result_chars) is not int or max_tool_result_chars < 1:
        raise ValueError("max_tool_result_chars must be a positive integer")
    calls = {
        message.get("call_id"): message.get("name")
        for message in messages
        if message.get("type") == "function_call"
    }
    outputs = [
        index
        for index, message in enumerate(messages)
        if message.get("type") == "function_call_output"
    ]
    latest = {}
    for index in outputs:
        name = calls.get(messages[index].get("call_id"))
        if name in {"search", "read_source"}:
            latest[name] = index
    required = set(latest.values())
    projected = [dict(message) for message in messages]
    for index in outputs:
        if index not in required:
            projected[index] = _omission(messages[index])
    if tool_result_chars(projected) > max_tool_result_chars:
        raise LimitReached("tool_context_size_limit")
    for index in reversed(outputs):
        if index in required or calls.get(messages[index].get("call_id")) == "search":
            continue
        previous = projected[index]
        projected[index] = dict(messages[index])
        if tool_result_chars(projected) > max_tool_result_chars:
            projected[index] = previous
    return projected
