"""Reject confounded comparisons and count paired outcomes on synthetic tasks."""

import copy
import unittest

from test_daloopa import bundle, record, rows, submission

from eval.scripts.compare_navigation import compare


class NavigationComparisonTests(unittest.TestCase):
    def setUp(self):
        self.bundle = bundle(rows(1))
        self.before = submission(self.bundle)
        self.before.update(
            status="finished",
            pricing={"input": 0.6, "output": 2.4},
            budget_usd=3,
            policy={
                "model": "synthetic",
                "limits": {"max_model_calls": 6},
                "max_output_tokens": 1800,
                "source_access": "web",
                "corpus_manifest_sha256": "synthetic",
                "exa_request_cap": 0.03,
            },
        )
        self.before["records"][0].update(record(119))
        self.after = copy.deepcopy(self.before)
        self.after["records"][0].update(record(120))

    def test_exact_gain_can_leave_tolerance_unchanged(self):
        result = compare(self.bundle, self.before, self.after)["groups"]["all_selected"]
        self.assertEqual(result["paired"]["numeric_exact"]["transitions"], {"fail_to_pass": 1})
        self.assertEqual(result["paired"]["tolerance_1pct"]["transitions"], {"pass_to_pass": 1})
        self.assertEqual(result["arms"][1]["quote_valid"], 1)

    def test_changed_budget_or_model_is_rejected(self):
        for field in ("model", "limits"):
            changed = copy.deepcopy(self.after)
            changed["policy"][field] = "different"
            with self.assertRaisesRegex(ValueError, "Policy mismatch"):
                compare(self.bundle, self.before, changed)

    def test_unfinished_or_uncertain_runs_are_rejected(self):
        self.after["status"] = "running"
        with self.assertRaisesRegex(ValueError, "finished, settled"):
            compare(self.bundle, self.before, self.after)
        self.after["status"] = "finished"
        self.after["records"][0]["cost_uncertain"] = True
        with self.assertRaisesRegex(ValueError, "finished, settled"):
            compare(self.bundle, self.before, self.after)
