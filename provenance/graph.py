"""Checkpointed, model-directed research with deterministic harness boundaries.

Only an explicit tool-boundary pause can resume automatically. An unexpected
process death during a provider request requires billing review before restarting.
"""

import json
import sqlite3
import time
from contextlib import ExitStack
from dataclasses import asdict
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from provenance.agent import Limits, Trace
from provenance.controls import Budget, LimitReached, deadline
from provenance.model import INSTRUCTIONS, validate_answer
from provenance.sources import TOOL_SCHEMAS
from provenance.transport import ProviderError

RUNTIME_POLICY = "research-v2-finalization"


class ResearchState(TypedDict):
    run_id: str
    identity: dict
    messages: list
    response: dict
    model_calls: int
    tool_calls: int
    tool_errors: int
    input_tokens: int
    output_tokens: int
    charged: float
    uncertain: bool
    seen: dict
    documents: dict
    events: list
    answer: dict | None
    answer_retries: int
    status: str
    reason: str | None
    phase: str
    elapsed: float


def run_graph(
    question,
    model,
    sources,
    limits=None,
    trace=None,
    *,
    checkpoint_path=None,
    thread_id=None,
    resume=False,
    pause_after_tools=False,
):
    """Run research; optional SQLite state supports explicit pause and resume.

    Resume requires the same question, model, limits, and corpus hashes. Completed
    threads are immutable. Failed or unexpectedly interrupted live work is never
    automatically retried because a provider may already have charged the request.
    """
    limits, trace = limits or Limits(), trace or Trace()
    if (resume or pause_after_tools) and not checkpoint_path:
        raise ValueError("Pause/resume requires --checkpoint")
    if checkpoint_path and not thread_id:
        raise ValueError("Checkpoint execution requires a stable thread_id")
    budget = Budget(limits.budget_usd)
    sources.budget = budget
    documents = {key: value for key, value in sources.documents.items() if "text_file" in value}
    identity = {
        "runtime_policy": RUNTIME_POLICY,
        "question": question,
        "model": model.name,
        "mode": model.mode,
        "limits": asdict(limits),
        "corpus": {key: value.get("sha256") for key, value in documents.items()},
        "web_enabled": bool(sources.exa_key),
        "retrieval_version": getattr(sources, "retrieval_version", "passage-v1"),
        "pricing": {
            "input_rate": getattr(model, "input_rate", None),
            "output_rate": getattr(model, "output_rate", None),
            "max_output": getattr(model, "max_output", None),
            "exa_cap": sources.exa_cap,
        },
    }
    current = {}
    started = time.monotonic()
    prior_elapsed = 0

    def attempt(state, node):
        # Separate committed transaction BEFORE external work. A crash leaves a
        # marker that must agree with a completed LangGraph node checkpoint.
        if not checkpoint_path:
            return
        counter = "model_calls" if node == "model" else "tool_calls"
        with sqlite3.connect(str(checkpoint_path)) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO research_attempts VALUES (?, ?, ?)",
                (thread_id, node, state[counter] + 1),
            )

    def load(state):
        budget.charged, budget.uncertain = state["charged"], state["uncertain"]
        sources.documents = state["documents"]
        sources.seen = {key: set(lines) for key, lines in state["seen"].items()}

    def save(state):
        state.update(
            charged=budget.charged,
            uncertain=budget.uncertain,
            seen={key: sorted(lines) for key, lines in sources.seen.items()},
            documents=sources.documents,
            events=trace.events.copy(),
            elapsed=prior_elapsed + time.monotonic() - started,
        )
        current.clear()
        current.update(state)
        return state

    def guard(operation):
        def node(state):
            state = dict(state)
            load(state)
            try:
                operation(state)
            except LimitReached as exc:
                state.update(status="stopped", reason=str(exc), phase="finished")
            except (ValueError, TypeError, KeyError, AttributeError, ProviderError) as exc:
                reason = (
                    str(exc)
                    if isinstance(exc, (ValueError, ProviderError))
                    else ("Invalid provider response shape")
                )
                state.update(status="failed", reason=reason, phase="finished")
            except KeyboardInterrupt:
                state.update(status="stopped", reason="user_interrupted", phase="finished")
            return save(state)

        return node

    def model_node(state):
        if state["model_calls"] >= limits.max_model_calls:
            raise LimitReached("model_call_limit")
        final_step = getattr(model, "final_step", None)
        final_only = callable(final_step) and (
            state["model_calls"] == limits.max_model_calls - 1
            or state["tool_calls"] >= limits.max_tool_calls
        )
        if final_only:
            boundary = (
                "tool_call_limit"
                if state["tool_calls"] >= limits.max_tool_calls
                else ("last_model_turn")
            )
            trace.emit("final_synthesis_required", reason=boundary)
            state["messages"] = state["messages"] + [
                {
                    "role": "user",
                    "content": (
                        "The execution boundary has been reached. Tool use is disabled for this "
                        "model turn. Return the final required JSON answer now, using only evidence "
                        "already returned by read_source and exact supported citations. If the read "
                        "evidence is insufficient, return an explicit abstention instead. "
                        "Do not request any further tools."
                    ),
                }
            ]
        attempt(state, "model")
        state["model_calls"] += 1
        trace.emit(
            "model_request",
            number=state["model_calls"],
            input=state["messages"].copy(),
            final_only=final_only,
        )
        step = final_step if final_only else model.step
        response = step(state["messages"], min(remaining(), limits.request_timeout_seconds), budget)
        trace.emit(
            "model_response",
            number=state["model_calls"],
            response=response,
            accounted_cost_usd=budget.charged,
        )
        state["response"] = response
        usage = response.get("usage", {})
        state["input_tokens"] += usage.get("input_tokens", 0)
        state["output_tokens"] += usage.get("output_tokens", 0)
        if response.get("status") != "completed":
            raise ProviderError("Model response did not complete")
        if not isinstance(response.get("output"), list):
            raise ProviderError("Model output must be a list")
        state["messages"] = state["messages"] + response["output"]
        if final_only and any(item.get("type") == "function_call" for item in response["output"]):
            raise ProviderError("Provider returned tool calls during final synthesis")
        state["phase"] = "model_returned"

    def tool_node(state):
        if sources.exa_key:
            attempt(state, "tools")
        messages = state["messages"].copy()
        state["messages"] = messages
        for call in state["response"]["output"]:
            if call.get("type") != "function_call":
                continue
            if state["tool_calls"] >= limits.max_tool_calls:
                if not callable(getattr(model, "final_step", None)):
                    raise LimitReached("tool_call_limit")
                if not isinstance(call.get("call_id"), str):
                    raise ProviderError("Tool call missing call_id")
                result = {
                    "error": "tool_call_limit: call was not executed; synthesize final answer"
                }
                trace.emit("tool_call_skipped", call=call, reason="tool_call_limit", result=result)
                messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": json.dumps(result),
                    }
                )
                continue
            if not isinstance(call.get("call_id"), str):
                raise ProviderError("Tool call missing call_id")
            state["tool_calls"] += 1
            trace.emit("tool_request", call=call)
            tool_start = time.monotonic()
            try:
                args = json.loads(call.get("arguments", ""))
            except (json.JSONDecodeError, TypeError):
                result = {"error": "Tool arguments must be valid JSON"}
            else:
                result = sources.call(
                    call.get("name"), args, min(remaining(), limits.request_timeout_seconds)
                )
            state["tool_errors"] += int("error" in result)
            trace.emit(
                "tool_result",
                call_id=call["call_id"],
                result=result,
                latency_seconds=time.monotonic() - tool_start,
                accounted_cost_usd=budget.charged,
            )
            messages.append(
                {
                    "type": "function_call_output",
                    "call_id": call["call_id"],
                    "output": json.dumps(result),
                }
            )
        state["phase"] = "paused" if pause_after_tools else "tools_returned"

    def answer_node(state):
        text = "".join(
            content.get("text", "")
            for item in state["response"]["output"]
            if item.get("type") == "message"
            for content in item.get("content", [])
            if content.get("type") == "output_text"
        )
        try:
            state["answer"] = validate_answer(json.loads(text), sources)
        except ValueError as exc:
            retries = state.get("answer_retries", 0)
            trace.emit("final_answer_rejected", reason=str(exc), repair_available=retries == 0)
            if retries:
                raise
            state["answer_retries"] = 1
            state["messages"] = state["messages"] + [
                {
                    "role": "user",
                    "content": (
                        f"Final answer validation rejected your answer: {exc}. "
                        "You have one opportunity to repair the final answer. "
                        "Use only sources and lines actually returned by read_source. "
                        "Every quote must be an exact contiguous excerpt from its cited lines; "
                        "do not add ellipses, combine noncontiguous fragments, or cite unread lines. "
                        "Call read_source for any missing evidence if necessary, then return "
                        "the required JSON answer. Existing execution and spending limits still apply."
                    ),
                }
            ]
            state["phase"] = "answer_repair"
            return
        state.update(status="completed", phase="finished")

    def route_model(state):
        if state["status"] != "running":
            return END
        return (
            "tools"
            if any(item.get("type") == "function_call" for item in state["response"]["output"])
            else "answer"
        )

    builder = StateGraph(ResearchState)
    builder.add_node("model", guard(model_node))
    builder.add_node("tools", guard(tool_node))
    builder.add_node("answer", guard(answer_node))
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", route_model)
    builder.add_conditional_edges(
        "tools", lambda state: ("model" if state["status"] == "running" else END)
    )
    builder.add_conditional_edges(
        "answer", lambda state: ("model" if state["status"] == "running" else END)
    )
    config = {
        "configurable": {"thread_id": thread_id or trace.id},
        "recursion_limit": limits.max_model_calls * 3 + 5,
    }
    with ExitStack() as stack:
        if checkpoint_path:
            with sqlite3.connect(str(checkpoint_path)) as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS research_attempts ("
                    "thread_id TEXT PRIMARY KEY, node TEXT NOT NULL, sequence INTEGER NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS research_results ("
                    "thread_id TEXT PRIMARY KEY, report TEXT NOT NULL)"
                )
        saver = (
            stack.enter_context(SqliteSaver.from_conn_string(str(checkpoint_path)))
            if (checkpoint_path)
            else None
        )
        graph = builder.compile(
            checkpointer=saver, interrupt_after=["tools"] if pause_after_tools else None
        )
        snapshot = graph.get_state(config) if saver else None
        if resume:
            if not snapshot or not snapshot.values:
                raise ValueError("No checkpoint exists for this thread")
            initial = dict(snapshot.values)
            with sqlite3.connect(str(checkpoint_path)) as connection:
                marker = connection.execute(
                    "SELECT node, sequence FROM research_attempts WHERE thread_id = ?",
                    (thread_id,),
                ).fetchone()
            if marker:
                counter = "model_calls" if marker[0] == "model" else "tool_calls"
                if initial[counter] < marker[1]:
                    raise ValueError(
                        "Uncommitted provider attempt; review billing before starting a new thread"
                    )
            if initial["identity"] != identity:
                raise ValueError("Resume question/model/limits/corpus differs from checkpoint")
            if initial["phase"] not in ("paused", "finished"):
                raise ValueError(
                    "Unexpected interruption; review provider billing before a new run"
                )
            if initial["phase"] == "finished" and initial["status"] != "completed":
                raise ValueError("Failed/stopped threads cannot resume; start a new thread")
            if initial["status"] == "completed":
                with sqlite3.connect(str(checkpoint_path)) as connection:
                    cached = connection.execute(
                        "SELECT report FROM research_results WHERE thread_id = ?", (thread_id,)
                    ).fetchone()
                if cached:
                    report = json.loads(cached[0])
                    trace.finish(report)
                    return report
            prior_elapsed = initial["elapsed"]
            trace.id = initial["run_id"]
            trace.events = initial["events"].copy()
            if trace.directory:
                (trace.directory / "trace.jsonl").write_text(
                    "".join(json.dumps(event, allow_nan=False) + "\n" for event in trace.events)
                )
            trace.emit("run_resumed", thread_id=thread_id)
            restore_model = getattr(model, "restore_checkpoint", None)
            if restore_model:
                restore_model(initial["model_calls"])
            current.update(initial)
            load(initial)
        else:
            if snapshot and snapshot.values:
                raise ValueError("Thread already exists; use resume or choose a new thread_id")
            sources.documents, sources.seen = documents, {}
            trace.emit(
                "run_started",
                question=question,
                mode=model.mode,
                model=model.name,
                limits=asdict(limits),
                source_mode="corpus+web" if sources.exa_key else ("frozen_corpus"),
                instructions=INSTRUCTIONS,
                tools=TOOL_SCHEMAS,
                corpus=identity["corpus"],
                runtime="langgraph",
                runtime_policy=RUNTIME_POLICY,
                retrieval_version=getattr(sources, "retrieval_version", "passage-v1"),
                pricing={
                    "input_usd_per_million": getattr(model, "input_rate", None),
                    "output_usd_per_million": getattr(model, "output_rate", None),
                    "exa_max_request_usd": sources.exa_cap,
                },
            )
            initial = ResearchState(
                run_id=trace.id,
                identity=identity,
                messages=[{"role": "user", "content": question}],
                response={},
                model_calls=0,
                tool_calls=0,
                tool_errors=0,
                input_tokens=0,
                output_tokens=0,
                charged=0,
                uncertain=False,
                seen={},
                documents=documents,
                events=trace.events.copy(),
                answer=None,
                answer_retries=0,
                status="running",
                reason=None,
                phase="started",
                elapsed=0,
            )
            current.update(initial)
        available = limits.timeout_seconds - prior_elapsed
        if available <= 0:
            current.update(status="stopped", reason="wall_clock_limit")
        elif not (resume and initial["status"] == "completed"):
            try:
                with deadline(available) as remaining:
                    result = graph.invoke(None if resume else initial, config)
                current.update(result)
            except LimitReached as exc:
                current.update(status="stopped", reason=str(exc))
            except KeyboardInterrupt:
                current.update(status="stopped", reason="user_interrupted")
        if current["status"] == "running":
            current.update(status="paused", reason="tool_boundary_pause")
    elapsed = prior_elapsed + time.monotonic() - started
    trace.emit(
        "run_finished",
        status=current["status"],
        reason=current["reason"],
        latency_seconds=elapsed,
        accounted_cost_usd=budget.charged,
        cost_uncertain=budget.uncertain,
    )
    report = {
        "run_id": trace.id,
        "mode": model.mode,
        "question": question,
        "status": current["status"],
        "stop_reason": current["reason"],
        "answer": current["answer"],
        "runtime": "langgraph",
        "runtime_policy": RUNTIME_POLICY,
        "thread_id": thread_id,
        "metrics": {
            "model_calls": current["model_calls"],
            "answer_retries": current.get("answer_retries", 0),
            "tool_calls": current["tool_calls"],
            "tool_errors": current["tool_errors"],
            "tool_error_rate": current["tool_errors"] / current["tool_calls"]
            if (current["tool_calls"])
            else None,
            "input_tokens": current["input_tokens"],
            "output_tokens": current["output_tokens"],
            "latency_seconds": elapsed,
            "accounted_cost_usd": budget.charged,
            "cost_uncertain": budget.uncertain,
        },
        "validation": "Structure, read evidence, and quote presence only; semantic accuracy needs grading.",
        "trace_path": str(trace.directory / "trace.jsonl") if trace.directory else None,
        "events": trace.events,
    }
    trace.finish(report)
    if checkpoint_path and report["status"] == "completed":
        with sqlite3.connect(str(checkpoint_path)) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO research_results VALUES (?, ?)",
                (thread_id, json.dumps(report, allow_nan=False)),
            )
    return report
