import hashlib
import json
import unittest
from unittest import mock

from eval.scripts.table_assessment_run import _canonical, _validate_protocol, run
from provenance.ingestion import ingest
from provenance.table_structure import extract_html_tables
from provenance.table_tools import TableSources
from tests import test_source_availability as temporal_tests
from tests.test_table_assessment import digest, write


class SidecarProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temporal = temporal_tests.TemporalAssessmentTests()
        self.temporal.setUp()
        self.addCleanup(self.temporal.doCleanups)
        self.f = self.temporal.fixture
        f = self.f
        original = f.root / "original.html"
        original.write_text(
            "<template><table><caption>needlemain decoy</caption>"
            "<tr><td>needlemain 999999</td></tr></table></template>" + original.read_text()
        )
        f.corpus = f.root / "versioned-corpus"
        manifest = ingest(
            {"sources": [{"id": "synthetic", "input_file": str(original)}]},
            f.corpus,
            html_text_version="native-html-text-v2",
        )
        self.original = f.corpus / manifest["sources"][0]["original_file"]
        f.binding = self.binding("native-html-tables-v3")

    def binding(self, version):
        sidecar = extract_html_tables(self.original, version=version)
        return {
            "original_sha256": sidecar["original_sha256"],
            "sidecar_version": version,
            "sidecar_sha256": hashlib.sha256(_canonical(sidecar).encode()).hexdigest(),
        }

    def prepare(self, blocked=False, version="native-html-tables-v3"):
        f = self.temporal.prepare(
            ["2025-05-01T00:00:00Z"] if blocked else [None],
            ["not_yet_available"] if blocked else [None],
        )
        protocol = json.loads(f.run_protocol.read_text())
        protocol.update(version="table-assessment-run-protocol-v4", sidecar_version=version)
        write(f.run_protocol, protocol)
        return f

    def execute(self):
        f = self.f
        original_read = type(f.annotations).read_bytes

        def no_labels(path):
            if path in {f.annotations, f.receipt}:
                raise AssertionError("Execution opened evaluator material")
            return original_read(path)

        with mock.patch.object(type(f.annotations), "read_bytes", new=no_labels):
            run(f.run_protocol, f.questions, f.corpus, f.report.parent)
        f.bind_grade()

    def test_v4_retrieves_and_grades_only_visible_geometry(self):
        f = self.prepare()
        self.execute()
        report = json.loads(f.report.read_text())
        self.assertEqual(report["sidecar_version"], "native-html-tables-v3")
        self.assertNotIn("999999", json.dumps(report["cases"]))
        self.assertNotEqual(self.binding("native-html-tables-v2"), f.binding)
        result = f.evaluate()
        self.assertEqual(result["mapped_denominator"], 1)
        self.assertEqual(result["complete_context_count"], 1)

    def test_v4_rejects_annotation_geometry_from_old_version(self):
        f = self.prepare()
        annotations = json.loads(f.annotations.read_text())
        annotations["sources"]["synthetic"] = self.binding("native-html-tables-v2")
        write(f.annotations, annotations)
        receipt = json.loads(f.receipt.read_text())
        receipt["annotations_sha256"] = digest(f.annotations)
        write(f.receipt, receipt)
        protocol = json.loads(f.run_protocol.read_text())
        protocol["assessment_receipt_sha256"] = digest(f.receipt)
        write(f.run_protocol, protocol)
        self.execute()
        with self.assertRaisesRegex(ValueError, "sidecar identity mismatch"):
            f.evaluate()

    def test_v4_report_cannot_claim_different_sidecar(self):
        f = self.prepare()
        self.execute()
        report = json.loads(f.report.read_text())
        report["sidecar_version"] = "native-html-tables-v2"
        write(f.report, report)
        f.bind_grade()
        with self.assertRaisesRegex(ValueError, "sidecar version mismatch"):
            f.evaluate()

    def test_v4_blocked_controls_do_not_construct_tools(self):
        f = self.prepare(blocked=True)
        with mock.patch(
            "eval.scripts.table_assessment_run.TableSources",
            side_effect=AssertionError("constructed"),
        ):
            self.execute()
        with mock.patch(
            "provenance.table_assessment.TableSources", side_effect=AssertionError("constructed")
        ):
            result = f.evaluate()
        self.assertEqual(result["availability_control_pass_count"], 1)
        self.assertEqual(json.loads(f.report.read_text())["cases"][0]["trace"], [])

    def test_version_is_required_valid_and_forbidden_on_old_protocols(self):
        f = self.prepare(blocked=True)
        protocol = json.loads(f.run_protocol.read_text())
        for version in [None, [], {}, True, "native-html-tables-v1"]:
            invalid = {**protocol, "sidecar_version": version}
            with self.subTest(version=version), self.assertRaises(ValueError):
                _validate_protocol(invalid)
        invalid = dict(protocol)
        del invalid["sidecar_version"]
        with self.assertRaisesRegex(ValueError, "fields must be exact"):
            _validate_protocol(invalid)
        for version in [
            "table-assessment-run-protocol-v1",
            "table-assessment-run-protocol-v2",
            "table-assessment-run-protocol-v3",
        ]:
            with self.subTest(version=version), self.assertRaises(ValueError):
                _validate_protocol({**protocol, "version": version})
        with self.assertRaisesRegex(ValueError, "sidecar version"):
            TableSources(f.corpus, sidecar_version="bad")
