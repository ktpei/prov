import importlib.util
import json
import unittest
from pathlib import Path

from provenance.context import project_messages, tool_result_chars

PATH = Path(__file__).resolve().parents[1] / "eval/reports/context-retention-2026-11-16/analyze.py"
spec = importlib.util.spec_from_file_location("context_retention_analysis", PATH)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def record(rank, size=100):
    return {
        "rank": rank,
        "status": "returned",
        "request": {"source_id": "s", "start_line": rank, "end_line": rank},
        "response": {
            "id": "s",
            "locator": f"L{rank}",
            "lines": [{"line": rank, "text": 'é\\"' * size}],
        },
    }


class ContextRetentionTests(unittest.TestCase):
    def test_exact_graph_serialization_and_full_retention(self):
        records = [record(1)]
        search = {"results": []}
        result = analysis.snapshots("question", search, records)
        history = [{"role": "user", "content": "question"}]
        history += analysis.pair("search", "search-1", {"query": "question"}, search)
        history += analysis.pair(
            "read_source", "read-1", records[0]["request"], records[0]["response"]
        )
        self.assertEqual(
            result["top_1"]["characters_after"], tool_result_chars(project_messages(history))
        )
        self.assertEqual(result["top_1"]["retained_read_ranks"], [1])
        self.assertEqual(
            result["top_1"]["read_hits"][0]["snippet"], records[0]["response"]["lines"][0]["text"]
        )
        self.assertEqual(result["top_5"]["attempted_read_slots"], 1)
        self.assertGreater(tool_result_chars(history), len(json.dumps(records[0]["response"])))

    def test_omission_locator_does_not_credit_evidence_and_prefixes_are_independent(self):
        records = [record(i, 100) for i in range(1, 6)]
        result = analysis.snapshots("q", {"results": []}, records, limit=3500)
        self.assertEqual(result["top_1"]["retained_read_ranks"], [1])
        self.assertIn(1, result["top_5"]["omitted_read_ranks"])
        self.assertEqual(result["top_5"]["read_hits"][0]["snippet"], "")
        self.assertIn(5, result["top_5"]["retained_read_ranks"])
        self.assertEqual(records[0]["response"]["lines"][0]["text"], 'é\\"' * 100)

    def test_blocked_context_gets_no_credit(self):
        result = analysis.snapshots("q", {"results": []}, [record(1, 1000)], limit=500)
        for value in result.values():
            self.assertEqual(value["status"], "blocked")
            self.assertEqual(value["retained_read_ranks"], [])
            self.assertEqual(value["read_hits"][0]["snippet"], "")

    def test_failed_newest_read_is_preserved_as_error_not_replaced(self):
        failed = {
            "rank": 2,
            "status": "failed",
            "request": {"source_id": "s", "start_line": 2, "end_line": 2},
            "response": None,
            "error": "failure",
        }
        result = analysis.snapshots("q", {"results": []}, [record(1, 200), failed], limit=600)
        self.assertEqual(result["top_3"]["status"], "projected")
        self.assertEqual(result["top_3"]["failed_read_ranks"], [2])
        self.assertEqual(result["top_3"]["retained_read_ranks"], [])
        self.assertEqual(result["top_3"]["omitted_read_ranks"], [1])

    def test_zero_hits_keeps_search_projection(self):
        result = analysis.snapshots("q", {"results": []}, [])
        self.assertTrue(
            all(v["status"] == "projected" and v["read_hits"] == [] for v in result.values())
        )

    def fixture(self):
        from unittest import mock

        from eval.scripts import parent_read_assessment
        from eval.scripts.table_assessment_run import runtime_digest
        from provenance.evidence_coverage import digest
        from tests import test_parent_read_assessment as fixtures

        helper = fixtures.ParentReadAssessmentTests()
        self.addCleanup(helper.doCleanups)
        protocol, prepared, corpus, report, packets, directory, output = helper.fixture()
        read_protocol = protocol.parent / "original-protocol.json"
        read_protocol.write_bytes(protocol.read_bytes())
        parent_read_assessment.run(read_protocol, prepared, corpus, report, directory)
        context_protocol = protocol.parent / "context-protocol.json"
        context_protocol.write_text(
            json.dumps(
                {
                    "version": "context-retention-protocol-v1",
                    "limit": 32000,
                    "analysis_sha256": digest(PATH),
                    "runtime_sha256": runtime_digest(),
                    "read_protocol_sha256": digest(read_protocol),
                    "run_sha256": digest(directory / "run.json"),
                    "journals": {"case-0.jsonl": digest(directory / "case-0.jsonl")},
                    "packets_sha256": digest(packets),
                }
            )
        )
        patches = mock.patch.multiple(
            analysis,
            READ_ROOT=protocol.parent,
            RUN_ROOT=directory,
            PREPARED=prepared,
            CORPUS=corpus,
            REPORT=report,
            PACKETS=packets,
        )
        return context_protocol, output, patches, packets, prepared

    def test_execute_projects_before_packets(self):
        from unittest import mock

        protocol, output, patches, packets, prepared = self.fixture()
        original = Path.read_bytes
        projected = False
        snapshot = analysis.snapshots

        def snapshots(*args, **kwargs):
            nonlocal projected
            result = snapshot(*args, **kwargs)
            projected = True
            return result

        def read(path):
            if path == packets and not projected:
                raise AssertionError("Packets opened before projection")
            return original(path)

        with (
            patches,
            mock.patch.object(Path, "read_bytes", new=read),
            mock.patch.object(analysis, "snapshots", side_effect=snapshots),
        ):
            result = analysis.execute(protocol, output)
        self.assertEqual(result["summary"]["top_1_complete_count"], 1)
        self.assertEqual(result["selected_denominator"], 1)

    def test_changed_prepared_input_during_grading_rejects_output(self):
        from unittest import mock

        protocol, output, patches, packets, prepared = self.fixture()
        actual = analysis.coverage

        def altered(*args, **kwargs):
            result = actual(*args, **kwargs)
            path = prepared / "inputs.json"
            path.write_bytes(path.read_bytes() + b"\n")
            return result

        with patches, mock.patch.object(analysis, "coverage", side_effect=altered):
            with self.assertRaisesRegex(ValueError, "frozen identity"):
                analysis.execute(protocol, output)
        self.assertFalse(output.exists())

    def test_extra_journal_added_during_grading_rejects_output(self):
        from unittest import mock

        protocol, output, patches, packets, prepared = self.fixture()
        actual = analysis.coverage

        def altered(*args, **kwargs):
            result = actual(*args, **kwargs)
            (analysis.RUN_ROOT / "extra.jsonl").write_text("unexpected")
            return result

        with patches, mock.patch.object(analysis, "coverage", side_effect=altered):
            with self.assertRaisesRegex(ValueError, "inventory"):
                analysis.execute(protocol, output)
        self.assertFalse(output.exists())

    def test_packet_schema_and_identity_are_validated(self):
        from unittest import mock

        for field in ["version", "corpus_manifest_sha256", "source", "declared"]:
            protocol, output, patches, packets, prepared = self.fixture()
            loader = analysis._load_object

            def load(raw, label, loader=loader, field=field):
                result = loader(raw, label)
                if label == "Context packets":
                    if field in ["version", "corpus_manifest_sha256"]:
                        result[field] = "wrong"
                    elif field == "source":
                        result["sources"]["REPORT"]["original_sha256"] = "0" * 64
                    else:
                        result["cases"][0]["source_id"] = "wrong"
                return result

            with patches, mock.patch.object(analysis, "_load_object", side_effect=load):
                with self.assertRaisesRegex(ValueError, "Packet"):
                    analysis.execute(protocol, output)
            self.assertFalse(output.exists())
