"""Model-directed loop with observable, deterministic stopping conditions."""

import json
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from provenance.controls import Budget, LimitReached, deadline, positive
from provenance.model import INSTRUCTIONS, validate_answer
from provenance.sources import TOOL_SCHEMAS
from provenance.transport import ProviderError


@dataclass
class Limits:
    max_model_calls: int = 8
    max_tool_calls: int = 10
    timeout_seconds: float = 90
    request_timeout_seconds: float = 30
    budget_usd: float = 0.5

    def __post_init__(self):
        for name in ("max_model_calls", "max_tool_calls"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("timeout_seconds", "request_timeout_seconds", "budget_usd"):
            positive(getattr(self, name), name)


class Trace:
    def __init__(self, log_dir=None):
        self.id = uuid.uuid4().hex
        self.events = []
        self.directory = None
        if log_dir:
            self.directory = Path(log_dir) / self.id
            self.directory.mkdir(parents=True, exist_ok=False)

    def emit(self, kind, **fields):
        event = {"event": kind, "time": datetime.now(timezone.utc).isoformat(), **fields}
        self.events.append(event)
        if self.directory:
            with (self.directory / "trace.jsonl").open("a") as stream:
                stream.write(json.dumps(event, allow_nan=False) + "\n")

    def finish(self, report):
        if self.directory:
            path = self.directory / "result.json"
            path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


def run(question, model, sources, limits=None, trace=None):
    limits, trace = limits or Limits(), trace or Trace()
    budget = Budget(limits.budget_usd)
    sources.budget = budget
    sources.seen = {}
    sources.documents = {
        key: source for key, source in sources.documents.items() if "text_file" in source
    }
    started = time.monotonic()
    model_calls = tool_calls = tool_errors = 0
    answer = None
    status, reason = "failed", None
    messages = [{"role": "user", "content": question}]
    trace.emit(
        "run_started",
        question=question,
        mode=model.mode,
        model=model.name,
        limits=asdict(limits),
        source_mode="corpus+web" if sources.exa_key else "frozen_corpus",
        retrieval_version=getattr(sources, "retrieval_version", "passage-v1"),
        instructions=INSTRUCTIONS,
        tools=TOOL_SCHEMAS,
        corpus={key: source.get("sha256") for key, source in sources.documents.items()},
        pricing={
            "input_usd_per_million": getattr(model, "input_rate", None),
            "output_usd_per_million": getattr(model, "output_rate", None),
            "exa_max_request_usd": sources.exa_cap,
        },
    )
    try:
        with deadline(limits.timeout_seconds) as remaining:
            while model_calls < limits.max_model_calls:
                model_calls += 1
                trace.emit("model_request", number=model_calls, input=messages.copy())
                response = model.step(
                    messages, min(remaining(), limits.request_timeout_seconds), budget
                )
                trace.emit(
                    "model_response",
                    number=model_calls,
                    response=response,
                    accounted_cost_usd=budget.charged,
                )
                if response.get("status") != "completed":
                    raise ProviderError("Model response did not complete")
                output = response.get("output")
                if not isinstance(output, list):
                    raise ProviderError("Model output must be a list")
                calls = [item for item in output if item.get("type") == "function_call"]
                messages.extend(output)
                if calls:
                    for call in calls:
                        if tool_calls >= limits.max_tool_calls:
                            raise LimitReached("tool_call_limit")
                        if not isinstance(call.get("call_id"), str):
                            raise ProviderError("Tool call missing call_id")
                        tool_calls += 1
                        trace.emit("tool_request", call=call)
                        tool_start = time.monotonic()
                        try:
                            args = json.loads(call.get("arguments", ""))
                        except (json.JSONDecodeError, TypeError):
                            result = {"error": "Tool arguments must be valid JSON"}
                        else:
                            result = sources.call(
                                call.get("name"),
                                args,
                                min(remaining(), limits.request_timeout_seconds),
                            )
                        tool_errors += int("error" in result)
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
                    continue
                text = "".join(
                    content.get("text", "")
                    for item in output
                    if item.get("type") == "message"
                    for content in item.get("content", [])
                    if content.get("type") == "output_text"
                )
                answer = validate_answer(json.loads(text), sources)
                status = "completed"
                break
            else:
                raise LimitReached("model_call_limit")
    except LimitReached as exc:
        status, reason = "stopped", str(exc)
    except (ValueError, TypeError, KeyError, AttributeError, ProviderError) as exc:
        reason = (
            str(exc)
            if isinstance(exc, (ValueError, ProviderError))
            else "Invalid provider response shape"
        )
    except KeyboardInterrupt:
        status, reason = "stopped", "user_interrupted"
    elapsed = time.monotonic() - started
    trace.emit(
        "run_finished",
        status=status,
        reason=reason,
        latency_seconds=elapsed,
        accounted_cost_usd=budget.charged,
        cost_uncertain=budget.uncertain,
    )
    report = {
        "run_id": trace.id,
        "mode": model.mode,
        "question": question,
        "status": status,
        "stop_reason": reason,
        "answer": answer,
        "metrics": {
            "model_calls": model_calls,
            "tool_calls": tool_calls,
            "tool_errors": tool_errors,
            "tool_error_rate": tool_errors / tool_calls if tool_calls else None,
            "latency_seconds": elapsed,
            "accounted_cost_usd": budget.charged,
            "cost_uncertain": budget.uncertain,
        },
        "validation": "Structure, read evidence, and quote presence only; semantic accuracy needs grading.",
        "trace_path": str(trace.directory / "trace.jsonl") if trace.directory else None,
        "events": trace.events,
    }
    trace.finish(report)
    return report
