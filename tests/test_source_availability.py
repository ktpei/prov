import json
import unittest
from unittest import mock

from eval.scripts.table_assessment_run import run, runtime_digest
from provenance.source_availability import availability, timestamp
from tests import test_table_assessment as grade_tests
from tests.test_table_assessment import digest, write


class AvailabilityTests(unittest.TestCase):
    def source(self, lower="2025-06-01T00:00:00-04:00", upper="2025-06-02T12:00:00Z"):
        return {
            "original_sha256": "a" * 64,
            "availability": {
                "original_sha256": "a" * 64,
                "not_before": lower,
                "observed_by": upper,
                "basis": "Invented metadata for an exact synthetic artifact",
            },
        }

    def test_three_valued_bounds_and_offset_equivalent_endpoints(self):
        source = self.source()
        checks = [
            (None, "not_requested", True),
            ("2025-06-01T03:59:59Z", "not_yet_available", False),
            ("2025-06-01T04:00:00Z", "unknown", False),
            ("2025-06-02T11:59:59Z", "unknown", False),
            ("2025-06-02T08:00:00-04:00", "available", True),
        ]
        for cutoff, state, allowed in checks:
            with self.subTest(cutoff=cutoff):
                result = availability(source, cutoff)
                self.assertEqual((result["state"], result["allowed"]), (state, allowed))
        exact = self.source("2025-06-01T00:00:00Z", "2025-06-01T00:00:00Z")
        self.assertEqual(availability(exact, "2025-06-01T00:00:00Z")["state"], "available")

    def test_missing_bounds_are_unknown_not_proof_of_unavailability(self):
        cutoff = "2025-06-01T00:00:00Z"
        self.assertEqual(availability({}, cutoff)["state"], "unknown")
        self.assertEqual(availability(self.source(None, None), cutoff)["state"], "unknown")
        self.assertEqual(
            availability(self.source(None, "2025-05-01T00:00:00Z"), cutoff)["state"], "available"
        )
        self.assertEqual(
            availability(self.source("2025-07-01T00:00:00Z", None), cutoff)["state"],
            "not_yet_available",
        )

    def test_malformed_metadata_rejected_even_without_cutoff(self):
        values = [
            "2025-06-01",
            "2025-06-01T00:00:00",
            "2025-02-30T00:00:00Z",
            "2025-06-01T00:00:00+01:99",
            True,
        ]
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                timestamp(value)
        invalid = [
            self.source("2025-07-01T00:00:00Z", "2025-06-01T00:00:00Z"),
            self.source("2025-06-01", None),
            self.source("2025-06-01T00:00:00+00:60", None),
        ]
        wrong = self.source()
        wrong["availability"]["original_sha256"] = "b" * 64
        invalid.append(wrong)
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(ValueError):
                availability(source, None)


class TemporalAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.fixture = grade_tests.AssessmentGradeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def prepare(self, cutoffs, expected_states):
        f = self.fixture
        path = f.corpus / "sources.json"
        manifest = json.loads(path.read_text())
        source = manifest["sources"][0]
        source["availability"] = {
            "original_sha256": source["original_sha256"],
            "not_before": "2025-06-01T00:00:00-04:00",
            "observed_by": "2025-06-02T12:00:00Z",
            "basis": "Synthetic original observed at declared upper bound",
        }
        write(path, manifest)
        cases = [
            {"id": f"q{i}", "source_id": "synthetic", "question": "needlemain", "as_of": cutoff}
            for i, cutoff in enumerate(cutoffs)
        ]
        write(f.questions, {"version": "table-assessment-questions-v2", "cases": cases})
        annotated = []
        for case, expected_state in zip(cases, expected_states, strict=True):
            if case["as_of"] is None:
                annotated.append(
                    {
                        "id": case["id"],
                        "source_id": "synthetic",
                        "disposition": "mapped",
                        "required_components": ["alpha"],
                        "reason": "",
                        "alternatives": [
                            {"table_id": "table-1", "components": {"alpha": ["table-1-r5-c1"]}}
                        ],
                    }
                )
            else:
                annotated.append(
                    {
                        "id": case["id"],
                        "source_id": "synthetic",
                        "disposition": "availability_control",
                        "required_components": [],
                        "alternatives": [],
                        "reason": "Synthetic time control",
                        "expected_availability": expected_state,
                    }
                )
        write(
            f.annotations,
            {
                "version": "table-assessment-annotations-v2",
                "questions_sha256": digest(f.questions),
                "corpus_manifest_sha256": digest(path),
                "sources": {"synthetic": f.binding},
                "cases": annotated,
            },
        )
        receipt = {
            "version": "table-assessment-receipt-v1",
            "questions_sha256": digest(f.questions),
            "annotations_sha256": digest(f.annotations),
            "corpus_manifest_sha256": digest(path),
            "runtime_sha256": runtime_digest(),
        }
        write(f.receipt, receipt)
        write(
            f.run_protocol,
            {
                "version": "table-assessment-run-protocol-v3",
                "search_version": "source-scoped-visible-row-bm25-v2",
                "assessment_receipt_sha256": digest(f.receipt),
                **{
                    k: receipt[k]
                    for k in ("questions_sha256", "corpus_manifest_sha256", "runtime_sha256")
                },
            },
        )
        return f

    def test_mixed_controls_keep_separate_denominators_and_permit_available_access(self):
        f = self.prepare(
            [None, "2025-05-31T23:59:59-04:00", "2025-06-01T12:00:00Z", "2025-06-02T12:00:00Z"],
            [None, "not_yet_available", "unknown", "available"],
        )
        report = run(f.run_protocol, f.questions, f.corpus, f.report.parent)
        self.assertEqual([len(c["trace"]) for c in report["cases"]], [2, 0, 0, 2])
        self.assertEqual(report["status_counts"]["availability_blocked"], 2)
        f.bind_grade()
        result = f.evaluate()
        self.assertEqual(result["selected_denominator"], 4)
        self.assertEqual(result["positive_denominator"], 1)
        self.assertEqual(result["availability_control_denominator"], 3)
        self.assertEqual(result["availability_control_pass_count"], 3)
        self.assertEqual(result["complete_context_count"], 1)

    def test_blocked_only_run_never_constructs_table_retrieval(self):
        f = self.prepare(["2025-05-31T23:59:59-04:00"], ["not_yet_available"])
        with mock.patch(
            "eval.scripts.table_assessment_run.TableSources",
            side_effect=AssertionError("future source read"),
        ):
            report = run(f.run_protocol, f.questions, f.corpus, f.report.parent)
        self.assertEqual(report["cases"][0]["status"], "availability_blocked")
        f.bind_grade()
        with mock.patch(
            "provenance.table_assessment.TableSources",
            side_effect=AssertionError("future source replay"),
        ):
            self.assertEqual(f.evaluate()["availability_control_pass_count"], 1)

    def test_invalid_cutoff_offset_is_rejected_before_retrieval(self):
        f = self.prepare(["2025-06-02T12:00:00Z"], ["available"])
        questions = json.loads(f.questions.read_text())
        questions["cases"][0]["as_of"] = "2025-06-02T12:00:00+00:60"
        write(f.questions, questions)
        protocol = json.loads(f.run_protocol.read_text())
        protocol["questions_sha256"] = digest(f.questions)
        write(f.run_protocol, protocol)
        with mock.patch("eval.scripts.table_assessment_run.TableSources") as constructor:
            with self.assertRaisesRegex(ValueError, "timestamps"):
                run(f.run_protocol, f.questions, f.corpus, f.report.parent)
        constructor.assert_not_called()
        self.assertFalse(f.report.parent.exists())

    def test_forged_always_blocking_behavior_is_rejected(self):
        f = self.prepare(["2025-06-02T12:00:00Z"], ["available"])
        report = run(f.run_protocol, f.questions, f.corpus, f.report.parent)
        report["cases"][0]["status"] = "availability_blocked"
        report["cases"][0]["trace"] = []
        write(f.report, report)
        f.bind_grade()
        with self.assertRaisesRegex(ValueError, "actual search trace"):
            f.evaluate()


if __name__ == "__main__":
    unittest.main()
