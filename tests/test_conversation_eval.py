"""Whole-conversation correctness cannot hide missing or incorrect turns."""

import unittest

from provenance.benchmarks import canonical_hash, prepare, score_run
from provenance.conversation_eval import score_conversation
from provenance.table_conversation_adapters import adapt_convfinqa


def task():
    return adapt_convfinqa(
        [
            {
                "id": "SYN_2024",
                "filename": "SYN/2024/page_1.pdf",
                "pre_text": [],
                "post_text": [],
                "table": [["Metric", "Value"], ["Value", "2"]],
                "annotation": {
                    "dialogue_break": ["Value?", "Double?", "Positive?"],
                    "turn_program": ["2", "multiply(2, 2)", "greater(4, 0)"],
                    "exe_ans_list": [2, 4, "yes"],
                },
            }
        ],
        source_split="dev",
    )[0]


class ConversationMetricTests(unittest.TestCase):
    def test_missing_turn_stays_in_denominator(self):
        output = {"turns": [{"turn_index": 0, "status": "completed", "output": {"answer": 2}}]}
        score = score_conversation(task(), output)
        self.assertFalse(score["passed"])
        self.assertEqual(score["turn_count"], 3)
        self.assertEqual(score["turn_passed_count"], 1)
        self.assertEqual(score["turn_accuracy"], 1 / 3)

    def test_whole_success_requires_every_turn_and_rejects_duplicate(self):
        rows = [
            {"turn_index": i, "status": "completed", "output": {"answer": answer}}
            for i, answer in enumerate([2, 4, "yes"])
        ]
        self.assertTrue(score_conversation(task(), {"turns": rows})["passed"])
        rows[1]["output"]["answer"] = 400
        self.assertFalse(score_conversation(task(), {"turns": rows})["passed"])
        with self.assertRaises(ValueError):
            score_conversation(task(), {"turns": [rows[0], rows[0]]})

    def test_stopped_conversation_preserves_completed_turn_scores(self):
        record = task()
        source = {
            "dataset": "convfinqa",
            "subset": "default",
            "source_split": "dev",
            "revision": "a" * 40,
            "sha256": "b" * 64,
            "url": "https://example.org",
            "license": "synthetic",
        }
        bundle = prepare(
            [record],
            source=source,
            count=1,
            seed=17,
            condition="agent_history",
            development_groups=["SYN/2024"],
        )
        submission = {
            "prepared_sha256": canonical_hash(bundle["manifest"]),
            "predictions": [
                {
                    "id": record["id"],
                    "status": "failed",
                    "output": {
                        "turns": [{"turn_index": 0, "status": "completed", "output": {"answer": 2}}]
                    },
                }
            ],
        }
        score = score_run(bundle, submission)
        self.assertEqual(score["conversation_metrics"]["turn_count"], 3)
        self.assertEqual(score["conversation_metrics"]["turn_passed_count"], 1)
        self.assertEqual(score["conversation_metrics"]["whole_conversation_accuracy"], 0)
        submission["predictions"][0]["output"]["turns"] = [
            {"turn_index": i, "status": "completed", "output": {"answer": answer}}
            for i, answer in enumerate([2, 4, "yes"])
        ]
        inconsistent = score_run(bundle, submission)
        self.assertEqual(inconsistent["conversation_metrics"]["turn_accuracy"], 1.0)
        self.assertEqual(inconsistent["conversation_metrics"]["whole_conversation_accuracy"], 0)
        self.assertEqual(inconsistent["tasks"][0]["status"], "conversation_status_inconsistent")
        self.assertEqual(inconsistent["tasks"][0]["completion_status"], "failed")


if __name__ == "__main__":
    unittest.main()
