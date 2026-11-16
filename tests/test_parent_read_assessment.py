import json
import unittest
from pathlib import Path
from unittest import mock

from eval.scripts import parent_read_assessment as assessment
from provenance.benchmarks import canonical_hash
from provenance.bounded_read import POLICY
from provenance.evidence_coverage import digest
from tests import test_evidence_coverage as fixtures


class ParentReadAssessmentTests(unittest.TestCase):
    def fixture(self):
        helper = fixtures.EvidenceCoverageTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        protocol, prepared, corpus, report, packets, output = helper.fixture()
        value = json.loads(protocol.read_text())
        del value["prepared_sha256"]
        value.update(
            version="parent-read-protocol-v1",
            policy=POLICY,
            plan_sha256=canonical_hash(assessment._replay(prepared, corpus, report)),
        )
        fixtures.write(protocol, value)
        return protocol, prepared, corpus, report, packets, output.parent / "run", output

    def test_run_never_opens_packets_and_grade_replays_before_labels(self):
        protocol, prepared, corpus, report, packets, directory, output = self.fixture()
        original = Path.read_bytes
        replayed = False

        def read(path):
            if path == packets and not replayed:
                raise AssertionError("Packet opened before read replay")
            return original(path)

        with mock.patch.object(Path, "read_bytes", new=read):
            result = assessment.run(protocol, prepared, corpus, report, directory)
        self.assertEqual(result["status"], "complete")
        real_run = assessment.run

        def replay(*args, **kwargs):
            nonlocal replayed
            result = real_run(*args, **kwargs)
            replayed = True
            return result

        with (
            mock.patch.object(Path, "read_bytes", new=read),
            mock.patch.object(assessment, "run", side_effect=replay),
        ):
            grade = assessment.grade(protocol, prepared, corpus, report, packets, directory, output)
        self.assertEqual(grade["summary"]["returned_reads"]["top_1_complete_count"], 1)
        self.assertEqual(grade["selected_denominator"], 1)
        with self.assertRaises(FileExistsError):
            assessment.run(protocol, prepared, corpus, report, directory)
        with self.assertRaisesRegex(ValueError, "already exists"):
            assessment.grade(protocol, prepared, corpus, report, packets, directory, output)

    def test_tampered_run_journal_or_inventory_rejects_before_labels(self):
        for kind in ["run", "journal", "extra"]:
            protocol, prepared, corpus, report, packets, directory, output = self.fixture()
            assessment.run(protocol, prepared, corpus, report, directory)
            if kind == "run":
                value = json.loads((directory / "run.json").read_text())
                value["cases"][0]["result"]["records"] = []
                fixtures.write(directory / "run.json", value)
            elif kind == "journal":
                (directory / "case-0.jsonl").write_text("forged\n")
            else:
                (directory / "case-99.jsonl").write_text("extra\n")
            packets.unlink()  # Replay rejection must precede attempted label access.
            with self.assertRaisesRegex(ValueError, "replay|inventory"):
                assessment.grade(protocol, prepared, corpus, report, packets, directory, output)
            self.assertFalse(output.exists())

    def test_interruption_preserves_case_without_successful_grade(self):
        protocol, prepared, corpus, report, packets, directory, output = self.fixture()
        with mock.patch.object(assessment, "read_ranked_passages", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                assessment.run(protocol, prepared, corpus, report, directory)
        value = json.loads((directory / "run.json").read_text())
        self.assertEqual(value["status"], "aborted")
        self.assertEqual(value["cases"][0]["status"], "running")
        with self.assertRaisesRegex(ValueError, "replay"):
            assessment.grade(protocol, prepared, corpus, report, packets, directory, output)
        self.assertFalse(output.exists())

    def test_post_read_input_mutation_aborts(self):
        for name in ["manifest.json", "tasks.json", "inputs.json", "benchmark_binding.json"]:
            protocol, prepared, corpus, report, packets, directory, output = self.fixture()
            target = (corpus if name == "benchmark_binding.json" else prepared) / name
            reader = assessment.read_ranked_passages

            def altered(*args, target=target, reader=reader, **kwargs):
                value = reader(*args, **kwargs)
                target.write_bytes(target.read_bytes() + b"\n")
                return value

            with mock.patch.object(assessment, "read_ranked_passages", side_effect=altered):
                with self.assertRaisesRegex(ValueError, "frozen identity"):
                    assessment.run(protocol, prepared, corpus, report, directory)
            self.assertEqual(json.loads((directory / "run.json").read_text())["status"], "aborted")

    def test_forged_search_and_projection_reject_before_reads(self):
        for kind in ["report", "plan"]:
            protocol, prepared, corpus, report, packets, directory, output = self.fixture()
            value = json.loads(protocol.read_text())
            if kind == "report":
                saved = json.loads(report.read_text())
                saved["tasks"][0]["retrieved_hits"][0]["end_line"] = 1
                fixtures.write(report, saved)
                value["report_sha256"] = digest(report)
            else:
                value["plan_sha256"] = "0" * 64
            fixtures.write(protocol, value)
            with mock.patch.object(assessment, "read_ranked_passages") as reader:
                with self.assertRaisesRegex(ValueError, "replay|plan"):
                    assessment.run(protocol, prepared, corpus, report, directory)
                reader.assert_not_called()
            self.assertFalse(directory.exists())

    def test_empty_and_failed_first_slots_keep_denominator_and_prefix(self):
        from provenance.sources import Sources

        for empty in [False, True]:
            protocol, prepared, corpus, report, packets, directory, output = self.fixture()
            plan = [
                {
                    "id": "one",
                    "hits": []
                    if empty
                    else [
                        {"source_id": "REPORT", "start_line": 2, "end_line": 2},
                        {"source_id": "REPORT", "start_line": 1, "end_line": 3},
                    ],
                }
            ]
            value = json.loads(protocol.read_text())
            value["plan_sha256"] = canonical_hash(plan)
            fixtures.write(protocol, value)
            original_read = Sources.read

            def read(source, sid, start, end, timeout, original_read=original_read):
                if start == 2:
                    raise ValueError("Synthetic failed first slot")
                return original_read(source, sid, start, end, timeout)

            # Isolate scheduler/grader integration; exact real-search replay is
            # exercised separately above, including forged-search rejection.
            with (
                mock.patch.object(assessment, "_replay", return_value=plan),
                mock.patch.object(Sources, "read", new=read),
            ):
                assessment.run(protocol, prepared, corpus, report, directory)
                grade = assessment.grade(
                    protocol, prepared, corpus, report, packets, directory, output
                )
            self.assertEqual(grade["selected_denominator"], 1)
            self.assertEqual(grade["summary"]["returned_reads"]["top_1_complete_count"], 0)
            self.assertEqual(
                grade["summary"]["returned_reads"]["top_3_complete_count"], 0 if empty else 1
            )
