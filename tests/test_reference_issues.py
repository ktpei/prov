"""Synthetic identity-binding tests for external reference-issue annotations."""

import copy
import unittest

from provenance.benchmarks import canonical_hash, model_input
from provenance.reference_issues import apply_reference_issues


def task(task_id="synthetic-1"):
    return {
        "id": task_id,
        "dataset": "finqa",
        "subset": "default",
        "source_split": "dev",
        "question": "What is the synthetic ratio?",
        "context": {"pre_text": [], "post_text": [], "table": [["value", "2"]]},
        "reference": {"answer": "2", "exe_ans": 2, "program": "identity(2)", "metric": "exact"},
        "metadata": {"filename": "synthetic.pdf"},
    }


def source(**changes):
    return {
        "dataset": "finqa",
        "subset": "default",
        "source_split": "dev",
        "revision": "a" * 40,
        "sha256": "b" * 64,
        **changes,
    }


def issue(row, **changes):
    return {
        "id": "finqa-unresolved-1",
        "dataset": row["dataset"],
        "subset": row["subset"],
        "source_split": row["source_split"],
        "revision": "a" * 40,
        "source_sha256": "b" * 64,
        "task_id": row["id"],
        "task_sha256": canonical_hash(row),
        "category": "ambiguous-denominator",
        "note": "The source does not specify a denominator convention.",
        "review": "Keep the task pending independent adjudication.",
        **changes,
    }


def registry(*issues):
    return {"version": "finance-reference-issues-v1", "issues": list(issues)}


class ReferenceIssueTests(unittest.TestCase):
    def test_applies_annotation_without_changing_model_input_or_gold(self):
        original = task()
        before = copy.deepcopy(original)
        annotated, applied = apply_reference_issues([original], source(), registry(issue(original)))

        self.assertEqual(applied, ["finqa-unresolved-1"])
        self.assertEqual(original, before)
        self.assertEqual(
            model_input(annotated[0], "supplied_context"),
            model_input(before, "supplied_context"),
        )
        self.assertEqual(annotated[0]["reference"]["answer"], before["reference"]["answer"])
        self.assertEqual(annotated[0]["reference"]["exe_ans"], before["reference"]["exe_ans"])
        self.assertEqual(annotated[0]["reference"]["program"], before["reference"]["program"])
        self.assertEqual(annotated[0]["question"], before["question"])
        self.assertEqual(annotated[0]["context"], before["context"])
        self.assertEqual(annotated[0]["metadata"], before["metadata"])
        self.assertIn("Unresolved reference issue", annotated[0]["reference"]["requires_review"])
        self.assertEqual(annotated[0]["reference"]["reference_issues"], applied)

    def test_preserves_existing_review_cause(self):
        original = task()
        original["reference"]["requires_review"] = "Existing answer-label disagreement."
        annotated, _ = apply_reference_issues([original], source(), registry(issue(original)))
        review = annotated[0]["reference"]["requires_review"]
        self.assertIn("Existing answer-label disagreement.", review)
        self.assertIn("finqa-unresolved-1", review)

    def test_rejects_stale_task_source_or_revision(self):
        original = task()
        current_issue = issue(original)
        stale = copy.deepcopy(original)
        stale["question"] = "Changed content"
        for tasks, current_source, candidate_issue in (
            ([stale], source(), current_issue),
            ([original], source(sha256="c" * 64), current_issue),
            ([original], source(revision="c" * 40), current_issue),
            ([original], source(source_split="test"), current_issue),
        ):
            with self.assertRaises(ValueError):
                apply_reference_issues(tasks, current_source, registry(candidate_issue))

    def test_ignores_unrelated_entries_and_keeps_deterministic_application_order(self):
        first, second = task("first"), task("second")
        unrelated = issue(task("other"))
        first_issue = issue(first, id="issue-first")
        second_issue = issue(second, id="issue-second")
        annotated, applied = apply_reference_issues(
            [second, first], source(), registry(unrelated, first_issue, second_issue)
        )
        self.assertEqual(applied, ["issue-second", "issue-first"])
        self.assertEqual(annotated[0]["reference"]["reference_issues"], ["issue-second"])
        self.assertEqual(annotated[1]["reference"]["reference_issues"], ["issue-first"])

    def test_rejects_duplicate_and_malformed_registry_entries(self):
        row = task()
        valid = issue(row)
        invalids = (
            registry(valid, {**valid}),
            registry(valid, {**valid, "id": "another-id"}),
            registry({**valid, "source_sha256": 7}),
            registry({**valid, "revision": "main"}),
            registry({**valid, "answer": "corrected"}),
            {"version": "other", "issues": []},
        )
        for invalid in invalids:
            with self.assertRaises(ValueError):
                apply_reference_issues([row], source(), invalid)


if __name__ == "__main__":
    unittest.main()
