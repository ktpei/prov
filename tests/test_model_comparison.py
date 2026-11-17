"""Synthetic aggregate comparison accounting; no inference requests."""

import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

from test_benchmark_run import prepared
from test_comparison_model import capability, response
from test_table_conversation_adapters import tatqa_group

from provenance.benchmarks import prepare
from provenance.model_comparison import run_comparison
from provenance.table_conversation_adapters import adapt_tatqa
from provenance.transport import post_json


def arms():
    return [
        {"id": effort, "capability": capability(), "effort": effort, "temperature": None}
        for effort in ("low", "high")
    ]


def reply():
    result = response()
    result["choices"][0]["message"]["content"] = '{"answer":"B"}'
    return result


class ModelComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "comparison"

    def run_case(self, request, **kwargs):
        settings = {
            "key": "SECRET",
            "budget_usd": 1,
            "per_arm_usd": 0.5,
            "per_attempt_usd": 0.1,
            "max_output": 1000,
            "request": request,
            **kwargs,
        }
        return run_comparison(prepared(), arms(), self.output, **settings)

    def test_one_inventory_interleaving_inputs_and_scoring(self):
        seen = []

        def request(url, body, headers, timeout):
            saved = json.loads((self.output / "comparison.json").read_text())
            pending = [r for r in saved["predictions"] if r["status"] == "pending"]
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["receipt"]["request"], body)
            self.assertNotIn("GOLD_SENTINEL", str(body))
            seen.append((body["reasoning"]["effort"], body["messages"][1]["content"]))
            return reply()

        result = self.run_case(request)
        self.assertEqual([x[0] for x in seen], ["low", "high", "high", "low", "low", "high"])
        for index in range(0, 6, 2):
            self.assertEqual(seen[index][1], seen[index + 1][1])
        self.assertAlmostEqual(result["accounted_cost_usd"], 6 * 0.0002)
        self.assertTrue(all(r["dispatched"] for r in result["predictions"]))
        scores = json.loads((self.output / "scores.json").read_text())
        self.assertEqual([s["selected_count"] for s in scores.values()], [3, 3])
        self.assertEqual([s["passed_count"] for s in scores.values()], [3, 3])
        self.assertEqual(result["scoring_status"], "finished")
        self.assertNotIn("SECRET", json.dumps(result))

    def test_shared_budget_and_arm_caps(self):
        def request(*args):
            result = reply()
            result["usage"]["cost"] = 0.02
            return result

        mock = Mock(side_effect=request)
        result = self.run_case(mock, budget_usd=0.05, per_attempt_usd=0.03)
        self.assertEqual(mock.call_count, 2)
        self.assertAlmostEqual(result["accounted_cost_usd"], 0.04)
        self.assertEqual(len(result["predictions"]), 6)
        self.assertEqual(sum(not r["dispatched"] for r in result["predictions"]), 4)

    def test_arm_cap_prevents_extra_dispatch(self):
        def request(*args):
            result = reply()
            result["usage"]["cost"] = 0.02
            return result

        mock = Mock(side_effect=request)
        result = self.run_case(mock, per_arm_usd=0.025, per_attempt_usd=0.025)
        self.assertEqual(mock.call_count, 2)
        for amount in result["arm_accounted_cost_usd"].values():
            self.assertAlmostEqual(amount, 0.02)
        self.assertEqual(sum(r["dispatched"] for r in result["predictions"]), 2)

    def test_billing_and_integrity_failures_stop_every_arm(self):
        for issue, expected in (
            ("cost", "stopped_for_billing_review"),
            ("provider", "stopped_for_integrity_review"),
        ):
            self.output = Path(self.tmp.name) / issue
            result = reply()
            if issue == "cost":
                result["usage"].pop("cost")
            else:
                result["provider"] = "Different"
            request = Mock(return_value=result)
            ledger = self.run_case(request)
            self.assertEqual(ledger["status"], expected)
            self.assertEqual(request.call_count, 1)
            self.assertEqual(sum(r["status"] == "skipped" for r in ledger["predictions"]), 5)
            self.assertEqual(len(ledger["predictions"]), 6)

    def test_interrupt_retains_pending_reservation_and_refuses_reuse(self):
        request = Mock(side_effect=KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            self.run_case(request)
        saved = json.loads((self.output / "comparison.json").read_text())
        self.assertEqual(saved["predictions"][0]["status"], "pending")
        self.assertEqual(saved["accounted_cost_usd"], 0.1)
        self.assertEqual(len(saved["predictions"]), 6)
        with self.assertRaises(FileExistsError):
            self.run_case(request)
        self.assertEqual(request.call_count, 1)

    def test_real_transport_status_is_durable_without_secrets_or_retry(self):
        for code in (400, 401, 429, 500):
            with self.subTest(code=code):
                self.output = Path(self.tmp.name) / str(code)
                error = urllib.error.HTTPError(
                    "https://SECRET.invalid", code, "SECRET", {"SECRET": "SECRET"}, None
                )
                with patch("provenance.transport.urllib.request.build_opener") as factory:
                    factory.return_value.open.side_effect = error
                    result = self.run_case(post_json)
                factory.return_value.open.assert_called_once()
                saved = json.loads((self.output / "comparison.json").read_text())
                self.assertEqual(saved, result)
                self.assertEqual(saved["status"], "stopped_for_billing_review")
                first = saved["predictions"][0]
                self.assertIn(f"API HTTP {code}; no automatic retry", first["failure"])
                self.assertTrue(first["cost_uncertain"])
                self.assertGreater(first["accounted_cost_usd"], 0)
                self.assertEqual(sum(r["status"] == "skipped" for r in saved["predictions"]), 5)
                self.assertNotIn("SECRET", json.dumps(saved))

    def test_invalid_inputs_and_arm_config_reject_before_output(self):
        request = Mock(return_value=reply())
        bundle = prepared()
        bundle["inputs"][0]["question"] = "altered"
        with self.assertRaises(ValueError):
            run_comparison(
                bundle,
                arms(),
                self.output,
                key="SECRET",
                budget_usd=1,
                per_arm_usd=0.5,
                per_attempt_usd=0.1,
                max_output=1000,
                request=request,
            )
        bad = arms()
        bad[1]["id"] = bad[0]["id"]
        with self.assertRaises(ValueError):
            run_comparison(
                prepared(),
                bad,
                self.output,
                key="SECRET",
                budget_usd=1,
                per_arm_usd=0.5,
                per_attempt_usd=0.1,
                max_output=1000,
                request=request,
            )
        self.assertFalse(self.output.exists())
        request.assert_not_called()

    def test_known_response_saved_before_parsing_and_deep_json_is_invalid(self):
        with patch(
            "provenance.model_comparison.parse_output", side_effect=RuntimeError("parser failure")
        ):
            with self.assertRaises(RuntimeError):
                self.run_case(Mock(return_value=reply()))
        saved = json.loads((self.output / "comparison.json").read_text())
        self.assertAlmostEqual(saved["accounted_cost_usd"], 0.0002)
        self.assertEqual(
            saved["predictions"][0]["response"]["provider_response"]["id"], "request-1"
        )
        self.output = Path(self.tmp.name) / "nested"
        result = reply()
        depth = 10000
        result["choices"][0]["message"]["content"] = "[" * depth + "0" + "]" * depth
        ledger = self.run_case(Mock(return_value=result))
        self.assertEqual(len(ledger["predictions"]), 6)
        self.assertTrue(
            all(r["parse_status"] == "invalid_json_depth" for r in ledger["predictions"])
        )
        self.assertAlmostEqual(ledger["accounted_cost_usd"], 0.0012)

    def test_metric_dependency_is_preflighted_before_dispatch(self):
        tasks = adapt_tatqa(
            [tatqa_group("table-" + str(i), "question-" + str(i)) for i in range(10)],
            source_split="dev",
        )
        source = {
            "url": "https://example.org",
            "revision": "a" * 40,
            "sha256": "b" * 64,
            "license": "synthetic",
            "dataset": "tatqa",
            "subset": tasks[0]["subset"],
            "source_split": "dev",
        }
        bundle = prepare(tasks, source=source, count=3, seed=17, condition="supplied_context")
        request = Mock()
        with patch(
            "provenance.official_metrics.load_tatqa_metric",
            side_effect=ValueError("dependency missing"),
        ):
            with self.assertRaisesRegex(ValueError, "dependency missing"):
                run_comparison(
                    bundle,
                    arms(),
                    self.output,
                    key="SECRET",
                    budget_usd=1,
                    per_arm_usd=0.5,
                    per_attempt_usd=0.1,
                    max_output=1000,
                    request=request,
                )
        request.assert_not_called()
        self.assertFalse(self.output.exists())
