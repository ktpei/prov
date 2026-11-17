"""Offline request, capability and provider-accounting comparison checks."""

import copy
import json
import unittest
from unittest.mock import Mock

from provenance.comparison_model import ComparisonClient, ComparisonIntegrityError, rates
from provenance.controls import Budget, LimitReached
from provenance.receipts import digest
from provenance.transport import ProviderError


def capability():
    return {
        "model": "synthetic/model",
        "response_model_ids": ["synthetic/model", "synthetic/snapshot"],
        "provider_name": "Synthetic",
        "provider_tag": "synthetic/standard",
        "supported_efforts": ["low", "high"],
        "supported_parameters": ["reasoning", "max_tokens"],
        "max_completion_tokens": 10000,
        "pricing": {
            "prompt": "0.000001",
            "completion": "0.000002",
            "input_cache_write": "0.00000125",
        },
    }


def response():
    return {
        "id": "request-1",
        "model": "synthetic/snapshot",
        "provider": "Synthetic",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 80,
            "total_tokens": 180,
            "completion_tokens_details": {"reasoning_tokens": 60},
            "prompt_tokens_details": {"cached_tokens": 10, "cache_write_tokens": 30},
            "cost": 0.0002,
        },
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "42"}}],
    }


def client(reply=None, **kwargs):
    request = Mock(return_value=response() if reply is None else reply)
    return ComparisonClient(
        "SECRET",
        capability(),
        effort="low",
        max_output=1000,
        instructions="Use the supplied packet",
        request=request,
        **kwargs,
    ), request


class ComparisonModelTests(unittest.TestCase):
    def test_exact_request_and_cost_without_reasoning_double_count(self):
        model, request = client()
        receipt = model.prepare("Question")
        budget = Budget(1)
        result = model.execute(receipt, 10, budget)
        body = request.call_args.args[1]
        self.assertEqual(body, receipt["request"])
        self.assertEqual(body["reasoning"], {"effort": "low"})
        self.assertNotIn("temperature", body)
        self.assertNotIn("tools", body)
        self.assertEqual(body["provider"]["only"], ["synthetic/standard"])
        self.assertFalse(body["provider"]["allow_fallbacks"])
        self.assertTrue(body["provider"]["require_parameters"])
        self.assertAlmostEqual(budget.charged, 0.0002)
        self.assertFalse(budget.uncertain)
        self.assertEqual(result["provider_response"]["usage"], response()["usage"])
        self.assertNotIn("SECRET", json.dumps([receipt, result, model.identity()]))

    def test_capability_validation_snapshot_and_identity(self):
        cap = capability()
        model = ComparisonClient("SECRET", cap, effort="high", max_output=1000, instructions="I")
        before = model.identity()
        cap["supported_efforts"].clear()
        self.assertEqual(model.identity(), before)
        self.assertEqual(model.prepare("Q")["request"]["reasoning"], {"effort": "high"})
        for kwargs in ({"effort": "max"}, {"temperature": 0}, {"max_output": True}):
            settings = {"effort": "low", "max_output": 1000, "instructions": "I", **kwargs}
            with self.assertRaises(ValueError):
                ComparisonClient("SECRET", capability(), **settings)
        cap = capability()
        cap["supported_parameters"].append("temperature")
        model = ComparisonClient(
            "SECRET", cap, effort="low", max_output=1000, instructions="I", temperature=0
        )
        self.assertEqual(model.prepare("Q")["request"]["temperature"], 0)

    def test_rehashed_settings_tampering_rejected_before_dispatch(self):
        model, request = client()
        for field, value in (
            ("reasoning", {"effort": "high"}),
            ("max_tokens", 2000),
            ("provider", {}),
        ):
            receipt = model.prepare("Q")
            receipt["request"][field] = value
            receipt["request_sha256"] = digest(receipt["request"])
            with self.assertRaises(ValueError):
                model.execute(receipt, 10, Budget(1))
        request.assert_not_called()

    def test_billed_truncation_and_empty_outputs_are_retained(self):
        for finish, content in (("length", "partial"), ("stop", "")):
            reply = response()
            reply["choices"][0].update(finish_reason=finish)
            reply["choices"][0]["message"]["content"] = content
            model, _ = client(reply)
            budget = Budget(1)
            result = model.execute(model.prepare("Q"), 10, budget)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["output_text"], content)
            self.assertAlmostEqual(budget.charged, 0.0002)
            self.assertFalse(budget.uncertain)

    def test_missing_or_invalid_cost_retains_reservation(self):
        for cost in (None, True, -1, float("nan")):
            reply = response()
            reply["usage"]["cost"] = cost
            model, _ = client(reply)
            budget = Budget(1)
            with self.assertRaises(ComparisonIntegrityError):
                model.execute(model.prepare("Q"), 10, budget)
            self.assertGreater(budget.charged, 0)
            self.assertTrue(budget.uncertain)

    def test_known_cost_survives_invalid_usage_or_routing(self):
        mutations = (
            lambda r: r.update(provider="Other"),
            lambda r: r.update(model="Other"),
            lambda r: r.update(id=None),
            lambda r: r["usage"].update(total_tokens=999),
            lambda r: r["usage"].update(completion_tokens_details=[]),
            lambda r: r["usage"]["completion_tokens_details"].update(reasoning_tokens=81),
            lambda r: r["usage"].update(completion_tokens=2000, total_tokens=2100),
            lambda r: r["choices"][0]["message"].update(tool_calls=[{"id": "unexpected"}]),
        )
        for mutate in mutations:
            reply = response()
            mutate(reply)
            model, _ = client(reply)
            budget = Budget(1)
            with self.assertRaises(ComparisonIntegrityError):
                model.execute(model.prepare("Q"), 10, budget)
            self.assertAlmostEqual(budget.charged, 0.0002)
            self.assertFalse(budget.uncertain)
            self.assertIsNotNone(model.last_response)

    def test_unknown_transport_failure_and_interrupt_keep_reservations(self):
        for error in (ProviderError("SECRET"), RuntimeError("SECRET"), KeyboardInterrupt()):
            model, request = client()
            request.side_effect = error
            budget = Budget(1)
            with self.assertRaises((ProviderError, KeyboardInterrupt)) as caught:
                model.execute(model.prepare("Q"), 10, budget)
            self.assertNotIn("SECRET", str(caught.exception))
            self.assertTrue(budget.uncertain)
            self.assertGreater(budget.charged, 0)
            self.assertEqual(request.call_count, 1)

    def test_preflight_rejections_do_not_dispatch_or_charge(self):
        model, request = client()
        for content, cap in (("Q", 0.000001), ("x" * 100000, 1)):
            budget = Budget(cap)
            with self.assertRaises(LimitReached):
                model.execute(model.prepare(content), 10, budget)
            self.assertEqual(budget.charged, 0)
            self.assertFalse(budget.uncertain)
        request.assert_not_called()

    def test_only_fixed_transport_diagnostics_survive_sanitization(self):
        safe = [
            "API redirects are disabled",
            "API response exceeds 2 MB limit",
            "API response must be an object",
            "API network, timeout, or JSON error; no automatic retry",
            *[f"API HTTP {code}; no automatic retry" for code in (400, 401, 429, 500)],
        ]
        unsafe = [
            "SECRET API HTTP 401; no automatic retry",
            "API HTTP 401; no automatic retry SECRET",
            "API HTTP 401; no automatic retry\n",
            "API HTTP ４０１; no automatic retry",
            "API HTTP 600; no automatic retry",
            "API HTTP 401; no automatic retry\nAuthorization: SECRET",
        ]
        for detail in safe + unsafe:
            with self.subTest(detail=detail):
                model, request = client()
                request.side_effect = ProviderError(detail)
                budget = Budget(1)
                with self.assertRaises(ProviderError) as caught:
                    model.execute(model.prepare("Q"), 10, budget)
                expected = (
                    "Comparison transport failed: " + detail
                    if detail in safe
                    else "Comparison transport failed (ProviderError)"
                )
                self.assertEqual(str(caught.exception), expected)
                self.assertTrue(model.last_dispatched)
                self.assertIsNone(model.last_response)
                self.assertTrue(budget.uncertain)
                self.assertGreater(budget.charged, 0)
                self.assertEqual(request.call_count, 1)

    def test_schedule_and_cache_reservations_and_overrun(self):
        pricing = copy.deepcopy(capability()["pricing"])
        pricing["overrides"] = [
            {"prompt": "0.000002", "completion": "0.000004", "input_cache_write": "0.0000025"}
        ]
        computed = rates(pricing)
        self.assertEqual(computed["input_reservation_per_token"], 0.0000045)
        self.assertEqual(computed["max_price"], {"prompt": 2, "completion": 4})
        reply = response()
        reply["usage"]["cost"] = 0.5
        model, _ = client(reply)
        budget = Budget(1)
        with self.assertRaisesRegex(LimitReached, "reservation_exceeded"):
            model.execute(model.prepare("Q"), 10, budget)
        self.assertEqual(budget.charged, 0.5)
        self.assertTrue(budget.uncertain)
        self.assertEqual(model.last_response["usage"]["cost"], 0.5)
        self.assertEqual(model.last_response["usage"], reply["usage"])
        self.assertEqual(model.last_response["choices"], reply["choices"])
