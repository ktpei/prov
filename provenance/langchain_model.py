"""LangChain chat adapter for OpenRouter, using the harness response contract."""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from provenance.context import project_messages, tool_result_chars
from provenance.controls import LimitReached, positive
from provenance.model import INSTRUCTIONS
from provenance.sources import TOOL_SCHEMAS
from provenance.transport import ProviderError


def chat_messages(messages):
    converted = [SystemMessage(content=INSTRUCTIONS)]
    for item in messages:
        if item.get("role") == "user":
            converted.append(HumanMessage(content=item["content"]))
        elif item.get("type") == "function_call":
            # Preserve the original JSON, including invalid arguments, for model recovery.
            converted.append(
                AIMessage(
                    content="",
                    additional_kwargs={
                        "tool_calls": [
                            {
                                "id": item["call_id"],
                                "type": "function",
                                "function": {"name": item["name"], "arguments": item["arguments"]},
                            }
                        ]
                    },
                )
            )
        elif item.get("type") == "function_call_output":
            converted.append(ToolMessage(content=item["output"], tool_call_id=item["call_id"]))
        elif item.get("type") == "message":
            converted.append(
                AIMessage(
                    content="".join(
                        part.get("text", "")
                        for part in item.get("content", [])
                        if part.get("type") == "output_text"
                    )
                )
            )
    # A provider can emit multiple calls in one assistant response. Group them so
    # no assistant tool-call message is followed by another assistant message.
    grouped = []
    for message in converted:
        if (
            isinstance(message, AIMessage)
            and message.additional_kwargs.get("tool_calls")
            and grouped
            and isinstance(grouped[-1], AIMessage)
            and grouped[-1].additional_kwargs.get("tool_calls")
        ):
            calls = grouped[-1].additional_kwargs["tool_calls"]
            grouped[-1] = AIMessage(
                content="",
                additional_kwargs={"tool_calls": calls + message.additional_kwargs["tool_calls"]},
            )
        else:
            grouped.append(message)
    return grouped


class OpenRouterModel:
    mode = "live_openrouter_langchain"

    def __init__(self, key, model, input_rate, output_rate, *, max_output=1800, chat=None):
        if not key or not model:
            raise ValueError("Set OPENROUTER_API_KEY and OPENROUTER_MODEL for a live run")
        self.name = model
        self.input_rate = positive(input_rate, "input token rate")
        self.output_rate = positive(output_rate, "output token rate")
        if type(max_output) is not int or max_output < 1:
            raise ValueError("max_output must be a positive integer")
        self.max_output = max_output
        client = chat or ChatOpenAI(
            model=model,
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            max_retries=0,
            max_tokens=max_output,
            temperature=0,
        )
        tools = [
            {
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema["description"],
                    "parameters": schema["parameters"],
                },
            }
            for schema in TOOL_SCHEMAS
        ]
        self.chat = client.bind_tools(tools, parallel_tool_calls=False)

    def step(self, messages, timeout, budget):
        before = tool_result_chars(messages)
        messages = project_messages(messages)
        projection = {
            "tool_result_characters_before": before,
            "tool_result_characters_after": tool_result_chars(messages),
        }
        serialized = json.dumps(
            {"instructions": INSTRUCTIONS, "messages": messages, "tools": TOOL_SCHEMAS},
            ensure_ascii=False,
        )
        input_bound = len(serialized.encode()) + 8192
        if input_bound > 100_000:
            raise LimitReached("input_size_limit")
        reserved = budget.reserve(
            (input_bound * self.input_rate + self.max_output * self.output_rate) / 1_000_000
        )
        settled = False
        try:
            response = self.chat.bind(timeout=timeout).invoke(chat_messages(messages))
            usage = response.usage_metadata or {}
            counts = [usage.get("input_tokens"), usage.get("output_tokens")]
            if not all(type(value) is int and value >= 0 for value in counts):
                raise ProviderError("Missing or invalid token usage; reservation retained")
            budget.settle(
                reserved, (counts[0] * self.input_rate + counts[1] * self.output_rate) / 1_000_000
            )
            settled = True
            finish = response.response_metadata.get("finish_reason")
            if finish not in (None, "stop", "tool_calls"):
                raise ProviderError(f"Model response did not complete: {finish}")
            calls = response.additional_kwargs.get("tool_calls", [])
            if not calls and response.tool_calls:
                calls = [
                    {
                        "id": call["id"],
                        "function": {"name": call["name"], "arguments": json.dumps(call["args"])},
                    }
                    for call in response.tool_calls
                ]
            if calls:
                output = [
                    {
                        "type": "function_call",
                        "call_id": call["id"],
                        "name": call["function"]["name"],
                        "arguments": call["function"]["arguments"],
                    }
                    for call in calls
                ]
            else:
                if not isinstance(response.content, str):
                    raise ProviderError("Expected a text final answer")
                output = [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": response.content}],
                    }
                ]
            return {
                "status": "completed",
                "output": output,
                "usage": {"input_tokens": counts[0], "output_tokens": counts[1]},
                "context_projection": projection,
            }
        except (LimitReached, ProviderError):
            budget.uncertain = budget.uncertain or not settled
            raise
        except Exception as exc:
            budget.uncertain = budget.uncertain or not settled
            # Provider exception bodies may contain request data. Never copy them into logs.
            raise ProviderError(f"OpenRouter request failed ({type(exc).__name__})") from None
