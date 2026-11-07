"""LangChain/OpenRouter adapter preserving the existing evidence/report contract."""

import json

from provenance.controls import LimitReached, positive
from provenance.model import INSTRUCTIONS
from provenance.sources import TOOL_SCHEMAS
from provenance.transport import ProviderError


def chat_messages(messages):
    """Translate the legacy trace format into LangChain-compatible chat messages."""
    result = [{"role": "system", "content": INSTRUCTIONS}]
    for item in messages:
        kind = item.get("type")
        if kind == "function_call":
            call = {
                "id": item["call_id"],
                "type": "function",
                "function": {"name": item["name"], "arguments": item["arguments"]},
            }
            if result[-1]["role"] == "assistant" and "tool_calls" in result[-1]:
                result[-1]["tool_calls"].append(call)
            else:
                result.append({"role": "assistant", "content": "", "tool_calls": [call]})
        elif kind == "function_call_output":
            result.append(
                {"role": "tool", "tool_call_id": item["call_id"], "content": item["output"]}
            )
        elif kind == "message":
            result.append(
                {
                    "role": item["role"],
                    "content": "".join(block.get("text", "") for block in item["content"]),
                }
            )
        elif kind == "reasoning":
            raise ProviderError("OpenAI reasoning items cannot be replayed across providers")
        else:
            result.append(item)
    return result


class OpenRouterModel:
    mode = "live_openrouter"

    def __init__(self, key, model, input_rate, output_rate, *, max_output=1600, client=None):
        if not key or not model:
            raise ValueError("Set OPENROUTER_API_KEY and OPENROUTER_MODEL for a live run")
        self.name = model
        self.input_rate = positive(input_rate, "input token rate")
        self.output_rate = positive(output_rate, "output token rate")
        self.max_output = max_output
        if client is None:
            try:
                from langchain_openai import ChatOpenAI
            except ImportError:
                raise ValueError("Install project dependencies: uv sync") from None
            client = ChatOpenAI(
                model=model,
                api_key=key,
                base_url="https://openrouter.ai/api/v1",
                max_tokens=max_output,
                max_retries=0,
            )
        tools = [
            {"type": "function", "function": {k: v for k, v in tool.items() if k != "type"}}
            for tool in TOOL_SCHEMAS
        ]
        self.client = client.bind_tools(tools, parallel_tool_calls=False)

    def step(self, messages, timeout, budget):
        chat = chat_messages(messages)
        input_bound = len(json.dumps([chat, TOOL_SCHEMAS], ensure_ascii=False).encode()) + 8192
        if input_bound > 100_000:
            raise LimitReached("input_size_limit")
        reservation = budget.reserve(
            (input_bound * self.input_rate + self.max_output * self.output_rate) / 1_000_000
        )
        settled = False
        try:
            response = self.client.invoke(chat, timeout=timeout)
            usage = response.usage_metadata or {}
            counts = [usage.get("input_tokens"), usage.get("output_tokens")]
            if not all(type(value) is int and value >= 0 for value in counts):
                raise ProviderError("Missing or invalid token usage; reservation retained")
            budget.settle(
                reservation,
                (counts[0] * self.input_rate + counts[1] * self.output_rate) / 1_000_000,
            )
            settled = True
            if response.invalid_tool_calls:
                raise ProviderError("Model returned malformed tool arguments")
            finish = response.response_metadata.get("finish_reason")
            if finish not in {"stop", "tool_calls"}:
                raise ProviderError("Model response did not complete")
            output = [
                {
                    "type": "function_call",
                    "name": call["name"],
                    "arguments": json.dumps(call["args"]),
                    "call_id": call["id"],
                }
                for call in response.tool_calls
            ]
            if not output:
                content = response.content
                if not isinstance(content, str):
                    content = "".join(
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    )
                output.append(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": content}],
                    }
                )
            return {"status": "completed", "output": output, "usage": usage}
        except LimitReached:
            raise
        except Exception as exc:
            # Provider exceptions may include request headers or response bodies.
            # Keep those out of persisted traces and user-facing reports.
            if isinstance(exc, ProviderError):
                raise
            budget.uncertain = True
            raise ProviderError("OpenRouter request failed; reservation retained") from None
        finally:
            # A failure before settlement leaves an estimated charge in the budget.
            # Known post-settlement validation errors retain their known usage.
            if not settled:
                budget.uncertain = True
