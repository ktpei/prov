"""Official metric semantics stay distinct from stricter financial support checks."""

import hashlib
import unittest
from pathlib import Path

from provenance.official_metrics import score_tatqa


def reference(answer, answer_type="arithmetic", scale=""):
    return {"answer": answer, "answer_type": answer_type, "scale": scale}


class OfficialMetricTests(unittest.TestCase):
    def test_vendored_source_matches_pinned_upstream_except_package_import(self):
        root = Path(__file__).resolve().parent.parent / "provenance/_vendor/tatqa"
        metric = (
            (root / "tatqa_metric.py")
            .read_bytes()
            .replace(b"from .tatqa_utils import *", b"from tatqa_utils import *")
        )
        self.assertEqual(
            hashlib.sha256(metric).hexdigest(),
            "2aeeac479f89f8c76300af1cc0e8d098eb86af84bc386b38b6ab4af484a6dea8",
        )
        self.assertEqual(
            hashlib.sha256((root / "tatqa_utils.py").read_bytes()).hexdigest(),
            "a84bb2f960737cf0a53733637a674cc4b20ef030a2be6a4b21dc2c4356f415ec",
        )
        self.assertEqual(
            hashlib.sha256((root / "LICENSE").read_bytes()).hexdigest(),
            "46e27ffbc49c3fd44a9595c2213f8a5f4319a81b53238e49ce1eec39e7e25662",
        )

    def test_zero_count_and_arithmetic(self):
        for gold, kind in [(0, "arithmetic"), ("0", "count")]:
            score = score_tatqa(reference(gold, kind), {"answer": 0, "scale": ""})
            self.assertEqual((score["exact_match"], score["f1"]), (1.0, 1.0))
        wrong = score_tatqa(reference(5), {"answer": 6, "scale": ""})
        self.assertEqual((wrong["exact_match"], wrong["f1"]), (0.0, 0.0))

    def test_equivalent_magnitude_and_scale_label_are_separate(self):
        score = score_tatqa(reference(2, scale="million"), {"answer": "2000", "scale": "thousand"})
        self.assertEqual(score["exact_match"], 1.0)
        self.assertEqual(score["scale_accuracy"], 0.0)
        wrong = score_tatqa(reference(25, scale="percent"), {"answer": "25", "scale": ""})
        self.assertEqual(wrong["exact_match"], 0.0)
        ratio = score_tatqa(reference(25, scale="percent"), {"answer": "0.25", "scale": ""})
        self.assertEqual(ratio["exact_match"], 1.0)
        self.assertEqual(ratio["scale_accuracy"], 0.0)

    def test_multispan_order_duplicates_and_empty_member_preserve_official_behavior(self):
        for gold, pred in [
            (["North", "South"], ["South", "North"]),
            (["A", "A"], ["A", "A"]),
            (["North", ""], ["North", ""]),
        ]:
            self.assertEqual(
                score_tatqa(reference(gold, "multi-span"), {"answer": pred, "scale": ""})[
                    "exact_match"
                ],
                1.0,
            )

    def test_benchmark_dispatch_preserves_official_fields(self):
        from provenance.benchmarks import score_answer

        task = {
            "id": "synthetic",
            "dataset": "tatqa",
            "reference": {**reference(2, scale="million"), "metric": "tatqa_official_em_f1"},
        }
        result = score_answer(task, {"answer": 2000, "scale": "thousand"})
        self.assertTrue(result["passed"])
        self.assertEqual(result["exact_match"], 1.0)
        self.assertEqual(result["f1"], 1.0)
        self.assertEqual(result["scale_accuracy"], 0.0)

    def test_scientific_notation_cannot_match_only_its_mantissa(self):
        for value in (1e-5, 1e20, "1e20", "1e-5", "1e20 million"):
            score = score_tatqa(reference(1), {"answer": value, "scale": ""})
            self.assertEqual(score["exact_match"], 0.0)
        self.assertEqual(
            score_tatqa(reference(1), {"answer": 1.0, "scale": ""})["exact_match"], 1.0
        )

    def test_nonfinite_boolean_extra_fields_and_bad_scale_fail(self):
        for prediction in [
            {"answer": True, "scale": ""},
            {"answer": float("nan"), "scale": ""},
            {"answer": 5, "scale": "trillion"},
            {"answer": 5, "scale": "", "extra": "unsupported"},
            {"answer": [], "scale": ""},
            {"answer": ["", "  "], "scale": ""},
            {"answer": "", "scale": ""},
        ]:
            self.assertEqual(score_tatqa(reference(5), prediction)["status"], "invalid_output")


if __name__ == "__main__":
    unittest.main()
