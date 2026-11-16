"""Adversarial projection, sampling, scoring, and denominator checks."""

import copy
import unittest

from provenance.benchmarks import (
    canonical_hash,
    model_input,
    prepare,
    score_answer,
)
from provenance.benchmarks import (
    score_run as raw_score_run,
)


def score_run(bundle, predictions):
    return raw_score_run(
        bundle, {"prepared_sha256": canonical_hash(bundle["manifest"]), "predictions": predictions}
    )


def task(number=0, dataset="fineval"):
    return {
        "id": f"task-{number}",
        "dataset": dataset,
        "subset": "synthetic",
        "source_split": "test",
        "question": "Which option? A: one B: two",
        "context": {
            "pre_text": ["Inputs 10 and 2"],
            "post_text": [],
            "table": [["a", "b"]],
            "gold": "SECRET",
        },
        "reference": {
            "answer": "B",
            "exe_ans": 5,
            "metric": "choice_accuracy",
            "program": "SECRET",
            "evidence": [
                {
                    "doc_name": "report",
                    "evidence_page_num": 0,
                    "evidence_text": "Revenue 5",
                    "secret": "GOLD",
                }
            ],
        },
        "metadata": {"doc_name": f"report-{number // 2}", "answer": "SECRET"},
    }


def bundle(dataset="fineval", condition="model_only"):
    return prepare(
        [task(i, dataset) for i in range(30)],
        source={
            "dataset": dataset,
            "subset": "synthetic",
            "source_split": "test",
            "url": "https://example.org/data",
            "revision": "a" * 40,
            "sha256": "b" * 64,
            "license": "synthetic test data",
        },
        count=5,
        seed=17,
        condition=condition,
    )


class BenchmarkTests(unittest.TestCase):
    def test_projection_allowlists_and_evidence_condition(self):
        fineval = model_input(task(), "model_only")
        self.assertEqual(fineval["context"], {})
        self.assertNotIn("SECRET", str(fineval))
        finqa = model_input(task(dataset="finqa"), "supplied_context")
        self.assertEqual(set(finqa["context"]), {"pre_text", "post_text", "table"})
        self.assertNotIn("SECRET", str(finqa))
        evidence = model_input(task(dataset="financebench"), "evidence_supplied")
        self.assertEqual(evidence["context"]["evidence"][0]["evidence_page_num"], 0)
        self.assertNotIn("GOLD", str(evidence))
        full = model_input(task(dataset="financebench"), "full_agent")
        self.assertNotIn("Revenue 5", str(full))
        with self.assertRaises(ValueError):
            model_input(task(), "full_agent")

    def test_selection_reproducible_and_group_partitioned(self):
        prepared = bundle()
        self.assertEqual(prepared, bundle())
        partition = prepared["manifest"]["partitions"]
        for number in range(0, 30, 2):
            self.assertEqual(partition[f"task-{number}"], partition[f"task-{number + 1}"])
        self.assertTrue(all(partition[t["id"]] == "dev" for t in prepared["tasks"]))
        self.assertEqual(prepared["manifest"]["source"]["source_split"], "test")

    def test_sampling_rejects_duplicate_and_unpinned_input(self):
        source = bundle()["manifest"]["source"]
        for tasks, current in [
            ([task(), task()], source),
            ([task()], {**source, "revision": "main"}),
        ]:
            with self.assertRaises(ValueError):
                prepare(tasks, source=current, count=1, seed=1, condition="model_only")

    def test_scoring_rejects_metadata_version_and_partition_changes(self):
        for change in ("version", "subset", "partition"):
            altered = bundle()
            if change == "version":
                altered["manifest"]["version"] = "future"
            elif change == "subset":
                altered["manifest"]["source"]["subset"] = "wrong"
            else:
                altered["manifest"]["partitions"][altered["tasks"][0]["id"]] = "internal_final"
            with self.assertRaises(ValueError):
                score_run(altered, [])

    def test_selection_is_order_invariant_and_oversampling_fails(self):
        first = bundle()
        records = [task(i) for i in reversed(range(30))]
        second = prepare(
            records, source=first["manifest"]["source"], count=5, seed=17, condition="model_only"
        )
        self.assertEqual(first, second)
        with self.assertRaisesRegex(ValueError, "eligible"):
            prepare(
                records,
                source=first["manifest"]["source"],
                count=31,
                seed=17,
                condition="model_only",
            )

    def test_choice_rejects_explanations_and_multiple_answers(self):
        self.assertTrue(score_answer(task(), {"answer": "B"})["passed"])
        for value in ("A or B", "The answer is B", True, None, "BB", "b"):
            self.assertFalse(score_answer(task(), {"answer": value})["passed"])
        self.assertFalse(score_answer(task(), {"answer": "B", "extra": "unsupported"})["passed"])

    def test_finqa_does_not_conflate_percent_boolean_or_nonfinite(self):
        record = task(dataset="finqa")
        record["reference"]["exe_ans"] = 0.25
        self.assertTrue(score_answer(record, {"answer": "0.250"})["passed"])
        for value in (25, "25%", True, "NaN", float("inf"), "0.25 dollars"):
            self.assertFalse(score_answer(record, {"answer": value})["passed"])
        record["reference"]["exe_ans"] = "yes"
        self.assertTrue(score_answer(record, {"answer": "yes"})["passed"])
        self.assertFalse(score_answer(record, {"answer": True})["passed"])

    def test_finqa_rounds_only_final_scalar_to_five_places(self):
        record = task(dataset="finqa")
        record["reference"]["exe_ans"] = 0.14203
        self.assertTrue(score_answer(record, {"answer": "0.142034"})["passed"])
        self.assertFalse(score_answer(record, {"answer": "0.142036"})["passed"])
        self.assertFalse(score_answer(record, {"answer": "14.203"})["passed"])
        self.assertFalse(score_answer(record, {"answer": "9" * 400})["passed"])

    def test_submission_is_bound_to_prepared_manifest(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            raw_score_run(bundle(), {"prepared_sha256": "wrong", "predictions": []})

    def test_missing_failed_and_invalid_all_remain_in_denominator(self):
        prepared = bundle()
        ids = prepared["manifest"]["selected_ids"]
        report = score_run(
            prepared,
            [
                {"id": ids[0], "status": "completed", "output": {"answer": "B"}},
                {"id": ids[1], "status": "failed", "output": {"answer": "B"}},
                {"id": ids[2], "status": "completed", "output": "B"},
            ],
        )
        self.assertEqual(report["selected_count"], 5)
        self.assertEqual(report["passed_count"], 1)
        self.assertEqual(report["accuracy"], 0.2)
        self.assertEqual(report["statuses"]["missing_or_incomplete"], 3)

    def test_semantic_review_never_becomes_automatic_accuracy(self):
        prepared = bundle("financebench", "evidence_supplied")
        predictions = [
            {"id": row["id"], "status": "completed", "output": {"answer_text": "Anything"}}
            for row in prepared["tasks"]
        ]
        report = score_run(prepared, predictions)
        self.assertIsNone(report["accuracy"])
        self.assertEqual(report["pending_review_count"], 5)
        self.assertEqual(report["passed_count"], 0)

    def test_rejects_tampering_and_duplicate_or_foreign_predictions(self):
        prepared = bundle()
        for key in ("tasks", "inputs"):
            altered = copy.deepcopy(prepared)
            altered[key][0]["question"] = "tampered"
            with self.assertRaises(ValueError):
                score_run(altered, [])
        row = {"id": prepared["tasks"][0]["id"], "status": "completed", "output": {"answer": "B"}}
        for predictions in ([row, row], [{**row, "id": "unknown"}]):
            with self.assertRaises(ValueError):
                score_run(prepared, predictions)


if __name__ == "__main__":
    unittest.main()
