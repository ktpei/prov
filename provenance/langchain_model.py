"""LangChain chat adapter for OpenRouter, using the harness response contract."""

import copy
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from provenance.context import project_messages, tool_result_chars
from provenance.controls import LimitReached, positive
from provenance.model import INSTRUCTIONS
from provenance.receipts import bound_tools, make_receipt, policy_identity
from provenance.sources import TOOL_SCHEMAS
from provenance.transport import ProviderError


def chat_messages(messages, *, instructions=INSTRUCTIONS):
    converted = [SystemMessage(content=instructions)]
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

    def __init__(
        self,
        key,
        model,
        input_rate,
        output_rate,
        *,
        max_output=1800,
        chat=None,
        instructions=INSTRUCTIONS,
        tool_schemas=None,
    ):
        if not key or not model:
            raise ValueError("Set OPENROUTER_API_KEY and OPENROUTER_MODEL for a live run")
        if not isinstance(instructions, str) or not instructions.strip():
            raise ValueError("Instructions must be nonempty text")
        self.instructions = instructions
        self.tool_schemas = copy.deepcopy(TOOL_SCHEMAS if tool_schemas is None else tool_schemas)
        self.name = model
        self.input_rate = positive(input_rate, "input token rate")
        self.output_rate = positive(output_rate, "output token rate")
        if type(max_output) is not int or max_output < 1:
            raise ValueError("max_output must be a positive integer")
        self.max_output = max_output
        self.last_response = None
        client = chat or ChatOpenAI(
            model=model,
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            max_retries=0,
            max_tokens=max_output,
            temperature=0,
        )
        tools = bound_tools(self.tool_schemas)
        self._bound_tools = copy.deepcopy(tools)
        self._generation = {
            "model": model,
            "max_tokens": max_output,
            "temperature": 0,
            "max_retries": 0,
            "parallel_tool_calls": False if tools else None,
        }
        self.chat = client.bind_tools(tools, parallel_tool_calls=False) if tools else client
        self._receipt_client, self._receipt_chat = client, self.chat
        self._generation["client_kind"] = (
            "ChatOpenAI" if isinstance(client, ChatOpenAI) else "injected-test-client"
        )

    def receipt_policy(self):
        if self.chat is not self._receipt_chat:
            raise ValueError("Receipt client binding changed")
        client = self._receipt_client
        if isinstance(client, ChatOpenAI):
            expected = {
                "model": self.name,
                "stream": False,
                "temperature": 0,
                "max_completion_tokens": self.max_output,
            }
            if (
                client._default_params != expected
                or client.max_retries != 0
                or client.openai_api_base != "https://openrouter.ai/api/v1"
            ):
                raise ValueError("Receipt profile requires matching OpenRouter client settings")
            if self._bound_tools and self.chat.kwargs != {
                "tools": self._bound_tools,
                "parallel_tool_calls": False,
            }:
                raise ValueError("Receipt tools differ from actual client binding")
        if bound_tools(self.tool_schemas) != self._bound_tools:
            raise ValueError("Tool schemas differ from bound tools")
        if (
            self.name != self._generation["model"]
            or self.max_output != self._generation["max_tokens"]
        ):
            raise ValueError("Model configuration differs from bound client")
        return policy_identity(self.instructions, self.tool_schemas, dict(self._generation))

    def step_with_receipt(
        self, messages, timeout, budget, *, run_id, attempt_id, emit, final_only=False
    ):
        return self._step(
            messages,
            timeout,
            budget,
            final_only=final_only,
            receipt_context=(run_id, attempt_id, emit),
        )

    def step(self, messages, timeout, budget):
        return self._step(messages, timeout, budget, final_only=False)

    def final_step(self, messages, timeout, budget):
        """Use a remaining allowed model turn for synthesis with tools disabled."""
        return self._step(messages, timeout, budget, final_only=True)

    def _step(self, messages, timeout, budget, *, final_only, receipt_context=None):
        self.last_response = None
        history = messages
        before = tool_result_chars(messages)
        messages = project_messages(messages)
        projection = {
            "tool_result_characters_before": before,
            "tool_result_characters_after": tool_result_chars(messages),
        }
        serialized = json.dumps(
            {"instructions": self.instructions, "messages": messages, "tools": self.tool_schemas},
            ensure_ascii=False,
        )
        mapped = chat_messages(messages, instructions=self.instructions)
        if receipt_context is not None:
            run_id, attempt_id, emit = receipt_context
            policy = self.receipt_policy()
            emit(
                "model_input_receipt",
                receipt=make_receipt(
                    history,
                    messages,
                    mapped,
                    instructions=self.instructions,
                    schemas=self.tool_schemas,
                    config=policy["config"],
                    run_id=run_id,
                    attempt_id=attempt_id,
                    timeout=timeout,
                    final_only=final_only,
                ),
            )
        input_bound = len(serialized.encode()) + 8192
        if input_bound > 100_000:
            raise LimitReached("input_size_limit")
        reserved = budget.reserve(
            (input_bound * self.input_rate + self.max_output * self.output_rate) / 1_000_000
        )
        settled = False
        try:
            options = {"timeout": timeout}
            if final_only and self.tool_schemas:
                options["tool_choice"] = "none"
            if receipt_context is not None:
                emit("model_dispatch_started", attempt_id=attempt_id)
            response = self.chat.bind(**options).invoke(mapped)
            usage = response.usage_metadata or {}
            counts = [usage.get("input_tokens"), usage.get("output_tokens")]
            if not all(type(value) is int and value >= 0 for value in counts):
                raise ProviderError("Missing or invalid token usage; reservation retained")
            self.last_response = {
                "content": response.content if isinstance(response.content, str) else None,
                "finish_reason": response.response_metadata.get("finish_reason"),
                "usage": {"input_tokens": counts[0], "output_tokens": counts[1]},
            }
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
            if calls and (final_only or not self.tool_schemas):
                raise ProviderError("Provider returned tool calls during final synthesis")
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
