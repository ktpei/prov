"""Reject confounded comparisons and count paired outcomes on synthetic tasks."""

import copy
import unittest

from test_daloopa import bundle, record, rows, submission

from eval.scripts.compare_navigation import compare
from provenance.benchmarks import canonical_hash


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

    def test_unresolved_reference_still_gets_quote_integrity_check(self):
        self.bundle["tasks"][0]["status"] = "reference_review_required"
        self.bundle["manifest"]["tasks_sha256"] = canonical_hash(self.bundle["tasks"])
        # A full run retains unresolved references; quick selection excludes them.
        self.bundle["manifest"]["quick_ids"] = []
        for ledger in (self.before, self.after):
            ledger["profile"] = "full"
            ledger["prepared_sha256"] = canonical_hash(self.bundle["manifest"])
        result = compare(self.bundle, self.before, self.after)["groups"]["all_selected"]
        self.assertEqual(result["arms"][1]["scorable"], 0)
        self.assertEqual(result["arms"][1]["quote_valid"], 1)

    def test_retained_reservation_requires_unchanged_reviewed_record(self):
        row = self.after["records"][0]
        row["cost_uncertain"] = True
        self.after["continuations"] = [
            {"retained_uncertain_records": {row["id"]: canonical_hash(row)}}
        ]
        result = compare(self.bundle, self.before, self.after)["groups"]["all_selected"]
        self.assertEqual(result["arms"][1]["retained_uncertain_cost_records"], 1)
        row["accounted_cost_usd"] = 0.5
        with self.assertRaisesRegex(ValueError, "finished, settled"):
            compare(self.bundle, self.before, self.after)
