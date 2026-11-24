"""Continuation keeps dispatched attempts and uncertain reservations immutable."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from test_benchmark_run import fake, prepared, response
from test_daloopa import bundle, corpus, fake_model, rows

from provenance.benchmark_resume import continue_ledger, reviewed_uncertainty
from provenance.benchmark_run import run_prepared
from provenance.daloopa_run import run_benchmark
from provenance.transport import ProviderError


class ContinuationTests(unittest.TestCase):
    def test_tool_free_continuation_preserves_failure_and_charged_reservation(self):
        def fail(messages, timeout, budget):
            budget.reserve(0.01)
            budget.uncertain = True
            raise ProviderError("provider allowance exhausted")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = run_prepared(
                prepared(), fake(fail), root / "old", budget_usd=0.06, per_task_usd=0.02
            )
            prior = root / "old/submission.json"
            original = prior.read_bytes()
            callback = Mock(return_value=response())
            new = run_prepared(
                prepared(),
                fake(callback),
                root / "new",
                budget_usd=0.06,
                per_task_usd=0.02,
                continue_from=prior,
                retain_uncertain=True,
            )
            self.assertEqual(callback.call_count, 2)
            self.assertEqual(new["predictions"][0], old["predictions"][0])
            self.assertAlmostEqual(new["accounted_cost_usd"], 0.01)
            self.assertEqual(new["status"], "finished")
            self.assertEqual(prior.read_bytes(), original)
            self.assertTrue(reviewed_uncertainty(new, "predictions"))
            new["predictions"][0]["accounted_cost_usd"] = 0
            self.assertFalse(reviewed_uncertainty(new, "predictions"))

    def test_daloopa_continuation_never_retries_failure_or_reserved_issuer(self):
        failure = {
            "status": "failed",
            "answer": None,
            "stop_reason": "provider error",
            "metrics": {"accounted_cost_usd": 0.03, "cost_uncertain": True},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = bundle(rows(4, reserved=True))
            sources = corpus(root)
            old = run_benchmark(
                data,
                fake_model(),
                root / "old",
                profile="full",
                corpus=sources,
                execute=Mock(return_value=failure),
            )
            callback = Mock(
                return_value={
                    **failure,
                    "metrics": {"accounted_cost_usd": 0.01, "cost_uncertain": False},
                }
            )
            new = run_benchmark(
                data,
                fake_model(),
                root / "new",
                profile="full",
                corpus=sources,
                execute=callback,
                continue_from=root / "old/submission.json",
                retain_uncertain=True,
            )
            self.assertEqual(callback.call_count, 2)
            self.assertEqual(new["status"], "finished")
            self.assertAlmostEqual(new["accounted_cost_usd"], 0.05)
            for previous, current in zip(old["records"], new["records"], strict=True):
                if previous["status"] != "skipped":
                    self.assertEqual(previous, current)
            self.assertTrue(reviewed_uncertainty(new))

    def test_rejects_changed_policy_unsettled_rows_and_unreviewed_cost(self):
        base = {
            "status": "stopped_for_billing_review",
            "model": "frozen",
            "accounted_cost_usd": 0.01,
            "predictions": [
                {"id": "a", "status": "failed", "cost_uncertain": True},
                {"id": "b", "status": "skipped"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            prior = Path(tmp) / "prior.json"
            for change, reviewed, error in (
                ({}, False, "explicitly retain"),
                ({"model": "changed"}, True, "mismatch"),
            ):
                prior.write_text(json.dumps(base))
                with self.assertRaisesRegex(ValueError, error):
                    continue_ledger(
                        {**base, **change}, prior, rows_key="predictions", retain_uncertain=reviewed
                    )
            for status in ("pending", "not_started"):
                unsettled = copy.deepcopy(base)
                unsettled["predictions"][0]["status"] = status
                prior.write_text(json.dumps(unsettled))
                with self.assertRaisesRegex(ValueError, "Unsettled"):
                    continue_ledger(base, prior, rows_key="predictions", retain_uncertain=True)
