"""Single-request, tool-free model comparisons with explicit routing and billing."""

import json
import math
from decimal import Decimal

from provenance.controls import LimitReached, positive
from provenance.receipts import canonical, digest
from provenance.transport import ProviderError, post_json

POLICY = "openrouter-tool-free-comparison-v1"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


class ComparisonIntegrityError(ProviderError):
    """Stop the entire comparison: configuration/response integrity is uncertain."""


def clone(value):
    return json.loads(canonical(value))


def rates(pricing):
    """Maximum advertised schedule; reserve extra for cache writes conservatively."""
    schedules = [pricing, *pricing.get("overrides", [])]

    def maximum(field):
        values = [
            Decimal(str(schedule.get(field, pricing.get(field, "0")))) for schedule in schedules
        ]
        if any(not value.is_finite() or value < 0 for value in values):
            raise ValueError("Invalid capability pricing")
        return max(values)

    prompt = maximum("prompt")
    completion = maximum("completion")
    cache_write = maximum("input_cache_write")
    cache_read = maximum("input_cache_read")
    if prompt <= 0 or completion <= 0 or maximum("request") != 0:
        raise ValueError("Comparison requires positive token rates and no request fee")
    return {
        "input_reservation_per_token": float(max(prompt, cache_read) + cache_write),
        "output_reservation_per_token": float(completion),
        "max_price": {
            "prompt": float(prompt * 1_000_000),
            "completion": float(completion * 1_000_000),
        },
    }


class ComparisonClient:
    """Pinned metadata is a preflight input, not proof of provider compliance."""

    def __init__(
        self,
        key,
        capability,
        *,
        effort,
        max_output,
        instructions,
        temperature=None,
        request=post_json,
    ):
        capability = clone(capability)
        required = {
            "model",
            "response_model_ids",
            "provider_name",
            "provider_tag",
            "supported_efforts",
            "supported_parameters",
            "max_completion_tokens",
            "pricing",
        }
        if set(capability) != required:
            raise ValueError("Invalid comparison capability fields")
        for field in ("model", "provider_name", "provider_tag"):
            if not isinstance(capability[field], str) or not capability[field].strip():
                raise ValueError("Missing model/provider identity")
        for field in ("response_model_ids", "supported_efforts", "supported_parameters"):
            if (
                not isinstance(capability[field], list)
                or not capability[field]
                or not all(isinstance(v, str) and v for v in capability[field])
            ):
                raise ValueError("Invalid capability inventory")
        if not key or not isinstance(instructions, str) or not instructions.strip():
            raise ValueError("Comparison requires credentials and instructions")
        if not isinstance(effort, str) or effort not in capability["supported_efforts"]:
            raise ValueError("Unsupported explicit reasoning effort")
        if not {"reasoning", "max_tokens"} <= set(capability["supported_parameters"]):
            raise ValueError("Endpoint does not advertise required parameters")
        if (
            type(max_output) is not int
            or type(capability["max_completion_tokens"]) is not int
            or not 1 <= max_output <= capability["max_completion_tokens"]
        ):
            raise ValueError("Invalid output token ceiling")
        if temperature is not None and (
            type(temperature) not in (int, float)
            or temperature != 0
            or "temperature" not in capability["supported_parameters"]
        ):
            raise ValueError("Temperature must be omitted or supported zero")
        self._key, self._capability, self._request = key, capability, request
        self._rates = rates(capability["pricing"])
        self._settings = {
            "policy": POLICY,
            "capability_sha256": digest(capability),
            "effort": effort,
            "max_output": max_output,
            "temperature": temperature,
            "instructions": instructions,
            "rates": self._rates,
        }
        self.last_response = None
        self.last_dispatched = False

    def identity(self):
        return clone({**self._settings, "capability": self._capability})

    def prepare(self, user_content):
        if not isinstance(user_content, str) or not user_content.strip():
            raise ValueError("Comparison input must be nonempty text")
        cap = self._capability
        body = {
            "model": cap["model"],
            "messages": [
                {"role": "system", "content": self._settings["instructions"]},
                {"role": "user", "content": user_content},
            ],
            "reasoning": {"effort": self._settings["effort"]},
            "max_tokens": self._settings["max_output"],
            "stream": False,
            "provider": {
                "only": [cap["provider_tag"]],
                "allow_fallbacks": False,
                "require_parameters": True,
                "max_price": self._rates["max_price"],
            },
        }
        if self._settings["temperature"] is not None:
            body["temperature"] = self._settings["temperature"]
        receipt = {
            "policy": POLICY,
            "boundary": "application-json-not-provider-attestation",
            "endpoint": ENDPOINT,
            "identity_sha256": digest(self.identity()),
            "request": body,
            "request_sha256": digest(body),
        }
        return clone(receipt)

    def execute(self, receipt, timeout, budget):
        """Caller must durably persist this receipt/reservation before invoking."""
        self.last_response = None
        self.last_dispatched = False
        receipt = clone(receipt)
        try:
            expected = self.prepare(receipt["request"]["messages"][1]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Malformed comparison receipt") from exc
        if receipt != expected:
            raise ValueError("Comparison receipt differs from current identity")
        positive(timeout, "timeout")
        # Match the actual existing transport's JSON serialization, plus allowance.
        input_bound = len(json.dumps(receipt["request"], allow_nan=False).encode()) + 8192
        if input_bound > 100_000:
            raise LimitReached("input_size_limit")
        reserved = budget.reserve(
            input_bound * self._rates["input_reservation_per_token"]
            + self._settings["max_output"] * self._rates["output_reservation_per_token"]
        )
        settled = False
        try:
            try:
                self.last_dispatched = True
                response = self._request(
                    ENDPOINT, receipt["request"], {"Authorization": "Bearer " + self._key}, timeout
                )
            except Exception as exc:
                raise ProviderError(
                    "Comparison transport failed (" + type(exc).__name__ + ")"
                ) from None
            if not isinstance(response, dict):
                raise ComparisonIntegrityError("Malformed provider response")
            usage = response.get("usage")
            if not isinstance(usage, dict):
                raise ComparisonIntegrityError("Missing provider usage; reservation retained")
            cost = usage.get("cost")
            self.last_response = {
                "id": response.get("id") if isinstance(response.get("id"), str) else None,
                "model": response.get("model") if isinstance(response.get("model"), str) else None,
                "provider": response.get("provider")
                if isinstance(response.get("provider"), str)
                else None,
                "usage": {
                    "cost": cost if type(cost) in (int, float) and math.isfinite(cost) else None
                },
            }
            if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
                raise ComparisonIntegrityError(
                    "Missing or invalid provider cost; reservation retained"
                )
            snapshot_valid = True
            try:
                self.last_response = clone(
                    {
                        key: response.get(key)
                        for key in ("id", "model", "provider", "usage", "choices")
                    }
                )
            except (TypeError, ValueError):
                snapshot_valid = False
            # Charge known cost even if the answer or other metadata is invalid.
            budget.settle(reserved, cost)
            settled = True
            if not snapshot_valid:
                raise ComparisonIntegrityError("Provider metadata is not finite JSON")
            counts = [
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
            ]
            if (
                not all(type(value) is int and value >= 0 for value in counts)
                or counts[0] + counts[1] != counts[2]
            ):
                raise ComparisonIntegrityError("Invalid provider token accounting")
            if counts[0] > input_bound or counts[1] > self._settings["max_output"]:
                raise ComparisonIntegrityError(
                    "Provider token usage exceeds declared request bounds"
                )
            details = usage.get("completion_tokens_details", {})
            prompt_details = usage.get("prompt_tokens_details", {})
            details = {} if details is None else details
            prompt_details = {} if prompt_details is None else prompt_details
            if not isinstance(details, dict) or not isinstance(prompt_details, dict):
                raise ComparisonIntegrityError("Invalid provider token details")
            for detail, total, fields in (
                (details, counts[1], ("reasoning_tokens",)),
                (prompt_details, counts[0], ("cached_tokens", "cache_write_tokens")),
            ):
                for field in fields:
                    if field in detail and (
                        type(detail[field]) is not int or not 0 <= detail[field] <= total
                    ):
                        raise ComparisonIntegrityError("Invalid provider token detail count")
            if not isinstance(response.get("id"), str) or not response["id"]:
                raise ComparisonIntegrityError("Missing provider request identity")
            if (
                response.get("model") not in self._capability["response_model_ids"]
                or response.get("provider") != self._capability["provider_name"]
            ):
                raise ComparisonIntegrityError("Provider/model identity differs from declared arm")
            choices = response.get("choices")
            if (
                not isinstance(choices, list)
                or len(choices) != 1
                or not isinstance(choices[0], dict)
            ):
                raise ComparisonIntegrityError("Expected one provider choice")
            choice = choices[0]
            message = choice.get("message")
            if (
                not isinstance(message, dict)
                or message.get("tool_calls")
                or message.get("function_call")
            ):
                raise ComparisonIntegrityError("Comparison response is not tool-free")
            content = message.get("content")
            finished = (
                choice.get("finish_reason") == "stop"
                and isinstance(content, str)
                and bool(content.strip())
            )
            return {
                "status": "completed" if finished else "failed",
                "output_text": content if isinstance(content, str) else None,
                "finish_reason": choice.get("finish_reason"),
                "provider_response": self.last_response,
                "billing": {
                    "reserved_usd": reserved,
                    "reported_cost_usd": cost,
                    "rate_estimate_usd": counts[0] * self._rates["input_reservation_per_token"]
                    + counts[1] * self._rates["output_reservation_per_token"],
                    "settlement": "provider_reported_cost; reasoning_included_in_completion",
                },
                "request_sha256": receipt["request_sha256"],
            }
        except BaseException as exc:
            budget.uncertain = budget.uncertain or not settled
            if isinstance(exc, (ProviderError, LimitReached, KeyboardInterrupt, SystemExit)):
                raise
            raise ComparisonIntegrityError(
                "Comparison request failed (" + type(exc).__name__ + ")"
            ) from None
