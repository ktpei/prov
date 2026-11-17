import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from eval.scripts.table_assessment_run import _canonical, run, runtime_digest
from provenance.ingestion import ingest
from provenance.table_assessment import grade
from provenance.table_structure import extract_html_tables


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


class AssessmentGradeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        original = self.root / "original.html"
        original.write_text(
            "<table><caption>Invented facts</caption>"
            + "<tr><td>Header context</td></tr>" * 5
            + "<tr><td>Needlemain alpha</td><td>17</td></tr>"
            + "<tr><td>Needlemain beta</td><td>23</td></tr>"
            + "<tr><td hidden>999</td><td>Unrelated seven</td></tr>"
            + "<tr><td>Unrelated eight</td></tr>"
            + "<tr><td>Unrelated nine</td></tr></table>"
        )
        self.corpus = self.root / "corpus"
        manifest = ingest(
            {"sources": [{"id": "synthetic", "input_file": str(original)}]}, self.corpus
        )
        source = manifest["sources"][0]
        sidecar = extract_html_tables(self.corpus / source["original_file"])
        self.binding = {
            "original_sha256": sidecar["original_sha256"],
            "sidecar_version": sidecar["version"],
            "sidecar_sha256": hashlib.sha256(_canonical(sidecar).encode()).hexdigest(),
        }
        self.questions = self.root / "questions.json"
        self.annotations = self.root / "annotations.json"
        self.receipt = self.root / "receipt.json"
        self.run_protocol = self.root / "run-protocol.json"
        self.grade_protocol = self.root / "grade-protocol.json"
        self.report = self.root / "run" / "report.json"
        self.output = self.root / "grade"

    def prepare(self, edit=None, dispositions=("mapped",)):
        questions = {
            "version": "table-assessment-questions-v1",
            "cases": [
                {"id": f"q{i}", "source_id": "synthetic", "question": "needlemain"}
                for i in range(len(dispositions))
            ],
        }
        write(self.questions, questions)
        annotations = {
            "version": "table-assessment-annotations-v1",
            "questions_sha256": digest(self.questions),
            "corpus_manifest_sha256": digest(self.corpus / "sources.json"),
            "sources": {"synthetic": self.binding},
            "cases": [
                {
                    "id": f"q{i}",
                    "source_id": "synthetic",
                    "disposition": disposition,
                    "required_components": ["alpha", "beta"],
                    "reason": ""
                    if disposition == "mapped"
                    else "Necessary qualification unavailable",
                    "alternatives": [
                        {
                            "table_id": "table-1",
                            "components": {"alpha": ["table-1-r5-c1"], "beta": ["table-1-r6-c1"]},
                        }
                    ]
                    if disposition == "mapped"
                    else [],
                }
                for i, disposition in enumerate(dispositions)
            ],
        }
        if edit:
            edit(annotations)
        write(self.annotations, annotations)
        receipt = {
            "version": "table-assessment-receipt-v1",
            "questions_sha256": digest(self.questions),
            "annotations_sha256": digest(self.annotations),
            "corpus_manifest_sha256": digest(self.corpus / "sources.json"),
            "runtime_sha256": runtime_digest(),
        }
        write(self.receipt, receipt)
        protocol = {
            key: receipt[key]
            for key in ("questions_sha256", "corpus_manifest_sha256", "runtime_sha256")
        }
        protocol.update(
            version="table-assessment-run-protocol-v2",
            search_version="source-scoped-visible-row-bm25-v2",
            assessment_receipt_sha256=digest(self.receipt),
        )
        write(self.run_protocol, protocol)
        original_read = Path.read_bytes

        def no_annotation_access(path):
            if path in {self.annotations, self.receipt}:
                raise AssertionError("Retrieval opened evaluator material")
            return original_read(path)

        with mock.patch.object(Path, "read_bytes", new=no_annotation_access):
            run(self.run_protocol, self.questions, self.corpus, self.report.parent)
        self.bind_grade()

    def bind_grade(self):
        write(
            self.grade_protocol,
            {
                "version": "table-assessment-grade-protocol-v1",
                **{
                    name + "_sha256": digest(path)
                    for name, path in {
                        "run_protocol": self.run_protocol,
                        "questions": self.questions,
                        "annotations": self.annotations,
                        "report": self.report,
                        "receipt": self.receipt,
                    }.items()
                },
            },
        )

    def evaluate(self):
        return grade(
            self.grade_protocol,
            self.run_protocol,
            self.questions,
            self.report,
            self.annotations,
            self.receipt,
            self.corpus,
            self.output,
        )

    def test_complete_context_and_ineligible_cases_keep_fixed_denominator(self):
        self.prepare(dispositions=("mapped", "unmapped", "unresolved"))
        result = self.evaluate()
        self.assertEqual(result["selected_denominator"], 3)
        self.assertEqual(result["mapped_denominator"], 1)
        self.assertEqual(result["complete_context_count"], 1)
        self.assertEqual(
            [c["complete_context_present"] for c in result["cases"]], [True, False, False]
        )
        self.assertTrue(result["execution_replay_verified"])
        self.assertEqual(result["semantic_answer_correctness"], "not_measured")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.evaluate()

    def test_annotation_edits_after_run_cannot_be_rebound_only_at_grading(self):
        self.prepare()
        value = json.loads(self.annotations.read_text())
        value["cases"][0]["required_components"] = ["alpha"]
        write(self.annotations, value)
        self.bind_grade()
        with self.assertRaisesRegex(ValueError, "after commitment"):
            self.evaluate()
        self.assertFalse(self.output.exists())

    def test_empty_component_inventory_is_not_a_vacuous_pass(self):
        def edit(value):
            value["cases"][0]["required_components"] = []
            value["cases"][0]["alternatives"][0]["components"] = {}

        self.prepare(edit)
        with self.assertRaisesRegex(ValueError, "components.*nonempty"):
            self.evaluate()

    def test_unmapped_component_cannot_be_omitted_from_an_alternative(self):
        def edit(value):
            value["cases"][0]["required_components"].append("qualification")

        self.prepare(edit)
        with self.assertRaisesRegex(ValueError, "every required"):
            self.evaluate()

    def test_hidden_cells_cannot_be_gold_visible_evidence(self):
        def edit(value):
            value["cases"][0]["alternatives"][0]["components"]["alpha"] = ["table-1-r7-c0"]

        self.prepare(edit)
        with self.assertRaisesRegex(ValueError, "visible cells"):
            self.evaluate()

    def test_partial_alternatives_are_not_pooled(self):
        def edit(value):
            alternatives = value["cases"][0]["alternatives"]
            alternatives.append(copy.deepcopy(alternatives[0]))
            alternatives[0]["components"]["beta"] = ["table-1-r9-c0"]
            alternatives[1]["components"]["alpha"] = ["table-1-r9-c0"]

        self.prepare(edit)
        result = self.evaluate()
        self.assertEqual(result["complete_context_count"], 0)
        self.assertEqual(
            result["cases"][0]["alternatives"][0]["required_component_presence"],
            {"alpha": True, "beta": False},
        )

    def test_modified_response_even_with_rehashed_report_fails_replay_before_labels(self):
        self.prepare()
        value = json.loads(self.report.read_text())
        value["cases"][0]["trace"][1]["response"]["cells"][0]["text"] = "forged"
        trace = value["cases"][0]["trace"][1]
        encoded = _canonical(trace["response"]).encode()
        trace["response_canonical_sha256"] = hashlib.sha256(encoded).hexdigest()
        trace["response_unicode_characters"] = len(encoded.decode())
        trace["response_utf8_bytes"] = len(encoded)
        write(self.report, value)
        self.bind_grade()
        original = Path.read_bytes

        def forbid_annotations(path):
            if path == self.annotations:
                raise AssertionError("Labels opened before execution verification")
            return original(path)

        with mock.patch.object(Path, "read_bytes", new=forbid_annotations):
            with self.assertRaisesRegex(ValueError, "replay mismatch"):
                self.evaluate()

    def test_wrong_call_arguments_and_boolean_denominator_fail(self):
        self.prepare()
        original = json.loads(self.report.read_text())
        value = copy.deepcopy(original)
        value["cases"][0]["trace"][1]["args"]["row_indices"] = [True]
        write(self.report, value)
        self.bind_grade()
        with self.assertRaisesRegex(ValueError, "replay mismatch"):
            self.evaluate()
        value = copy.deepcopy(original)
        value["task_denominator"] = True
        write(self.report, value)
        self.bind_grade()
        with self.assertRaisesRegex(ValueError, "denominator"):
            self.evaluate()

    def test_duplicate_json_keys_and_incomplete_runs_rejected(self):
        self.prepare()
        value = json.loads(self.report.read_text())
        value["run_status"] = "interrupted"
        write(self.report, value)
        self.bind_grade()
        with self.assertRaisesRegex(ValueError, "completed"):
            self.evaluate()
        self.grade_protocol.write_text('{"version":"x","version":"y"}')
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            self.evaluate()


if __name__ == "__main__":
    unittest.main()
