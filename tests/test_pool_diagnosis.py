import importlib.util
import unittest
from pathlib import Path

PATH = (
    Path(__file__).resolve().parents[1]
    / "eval/assessments/financebench-page-ranking-v1/diagnose_pool.py"
)
spec = importlib.util.spec_from_file_location("pool_diagnosis", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PoolDiagnosisTests(unittest.TestCase):
    def test_minimum_size_then_lexicographic_ranks(self):
        result = module.minimum_cover([{1}, {2}, {1, 2}, {1, 2}], {1, 2})
        self.assertEqual(result["ranks"], [3])
        result = module.minimum_cover([{1}, {2}, {1}, {2}], {1, 2})
        self.assertEqual(result["ranks"], [1, 2])

    def test_gap_is_missing_but_disjoint_required_lines_can_combine(self):
        result = module.minimum_cover([{1, 2}, {4, 5}], {2, 3, 4})
        self.assertEqual(result["missing_lines"], [3])
        self.assertEqual(result["status"], "missing_from_pool")
        self.assertEqual(module.minimum_cover([{1}, {10}], {1, 10})["ranks"], [1, 2])

    def test_five_read_bound_and_twenty_fifth_candidate(self):
        result = module.minimum_cover([{i} for i in range(6)], set(range(6)))
        self.assertEqual(result["status"], "pool_complete_requires_more_than_five")
        self.assertEqual(module.minimum_cover([{i} for i in range(25)], {24})["ranks"], [25])

    def test_empty_evidence_and_oversized_pool_rejected(self):
        with self.assertRaises(ValueError):
            module.minimum_cover([{1}], set())
        with self.assertRaises(ValueError):
            module.minimum_cover([{1}] * 26, {1})
        self.assertEqual(module.minimum_cover([], {1})["status"], "missing_from_pool")
