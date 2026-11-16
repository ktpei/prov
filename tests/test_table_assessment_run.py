import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from eval.scripts import table_assessment_run
from provenance.ingestion import ingest
from provenance.table_tools import TableSources


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class TableAssessmentRunTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        first = self.root / "first.html"
        first.write_text(
            """<table><caption>Facts</caption>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Context one</td><td>1</td></tr>
<tr><td>Context two</td><td>2</td></tr>
<tr><td>Context three</td><td>3</td></tr>
<tr><td>Context four</td><td>4</td></tr>
<tr><td>Needle alpha</td><td>10</td></tr>
<tr><td>Needle beta</td><td>20</td></tr>
<tr><td>Needle gamma</td><td>30</td></tr>
<tr><td>Needle delta</td><td>40</td></tr>
</table>""",
            encoding="utf-8",
        )
        second = self.root / "second.html"
        second.write_text(
            """<table><tr><th>Item</th><th>Amount</th></tr>
<tr><td>Other context</td><td>1</td></tr>
<tr><td>More context</td><td>2</td></tr>
<tr><td>Still context</td><td>3</td></tr>
<tr><td>Last context</td><td>4</td></tr>
<tr><td>Unicode café metric</td><td>€5</td></tr></table>""",
            encoding="utf-8",
        )
        self.corpus = self.root / "corpus"
        ingest(
            {
                "sources": [
                    {"id": "first-source", "title": "First", "input_file": str(first)},
                    {"id": "second-source", "title": "Second", "input_file": str(second)},
                ]
            },
            self.corpus,
        )
        self.protocol_path = self.root / "protocol.json"
        self.questions_path = self.root / "questions.json"

    def write_inputs(self, cases, **protocol_overrides):
        questions = {"version": "table-assessment-questions-v1", "cases": cases}
        questions_raw = json.dumps(questions, ensure_ascii=False, indent=2).encode("utf-8")
        self.questions_path.write_bytes(questions_raw)
        manifest_raw = (self.corpus / "sources.json").read_bytes()
        protocol = {
            "version": "table-assessment-run-protocol-v1",
            "questions_sha256": digest(questions_raw),
            "corpus_manifest_sha256": digest(manifest_raw),
            "search_version": "source-scoped-visible-row-bm25-v2",
            "runtime_sha256": table_assessment_run.runtime_digest(),
        }
        protocol.update(protocol_overrides)
        self.protocol_path.write_text(json.dumps(protocol, indent=2), encoding="utf-8")
        return protocol

    def run_assessment(self, cases, output_name="output", **protocol_overrides):
        self.write_inputs(cases, **protocol_overrides)
        output = self.root / output_name
        report = table_assessment_run.run(
            self.protocol_path, self.questions_path, self.corpus, output
        )
        return report, output

    def test_real_run_uses_top_hit_first_three_rows_once_across_sources(self):
        cases = [
            {"id": "one", "source_id": "first-source", "question": "needle"},
            {"id": "two", "source_id": "second-source", "question": "café"},
        ]
        report, output = self.run_assessment(cases)

        self.assertEqual(report["task_denominator"], 2)
        self.assertEqual(report["status_counts"]["completed"], 2)
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(report["runtime_version"], "table-assessment-run-runtime-v1")
        self.assertEqual([len(case["trace"]) for case in report["cases"]], [2, 2])
        first_read = report["cases"][0]["trace"][1]
        self.assertEqual(first_read["tool"], "read_table")
        self.assertEqual(first_read["args"]["table_id"], "table-1")
        self.assertEqual(first_read["args"]["row_indices"], [5, 6, 7])
        self.assertNotIn("oracle", json.dumps(report).lower())
        self.assertNotIn("answer", json.dumps(report).lower())

        persisted = json.loads((output / "report.json").read_text())
        self.assertEqual(persisted["status_counts"], report["status_counts"])
        self.assertFalse((output / ".report.json.tmp").exists())
        for case in persisted["cases"]:
            for trace in case["trace"]:
                serialized = canonical(trace["response"])
                self.assertEqual(
                    trace["response_canonical_sha256"], digest(serialized.encode("utf-8"))
                )
                self.assertEqual(trace["response_unicode_characters"], len(serialized))
                self.assertEqual(trace["response_utf8_bytes"], len(serialized.encode("utf-8")))
                self.assertGreaterEqual(trace["latency_seconds"], 0)

    def test_mutation_during_execution_invalidates_durable_report(self):
        cases = [{"id": "one", "source_id": "first-source", "question": "needle"}]
        self.write_inputs(cases)
        original_call = TableSources.call

        def mutate(instance, name, args, timeout):
            result = original_call(instance, name, args, timeout)
            self.questions_path.write_text("changed during execution")
            return result

        output = self.root / "mutated"
        with mock.patch.object(TableSources, "call", new=mutate):
            with self.assertRaisesRegex(ValueError, "inputs changed"):
                table_assessment_run.run(
                    self.protocol_path, self.questions_path, self.corpus, output
                )
        report = json.loads((output / "report.json").read_text())
        self.assertEqual(report["run_status"], "invalid")
        self.assertEqual(len(report["cases"][0]["trace"]), 2)
        self.assertNotIn("post_run_integrity_verified", report)

    def test_keyboard_interrupt_preserves_search_and_remaining_denominator(self):
        cases = [
            {"id": "one", "source_id": "first-source", "question": "needle"},
            {"id": "two", "source_id": "second-source", "question": "café"},
        ]
        self.write_inputs(cases)
        original_call = TableSources.call

        def interrupt_read(instance, name, args, timeout):
            if name == "read_table":
                raise KeyboardInterrupt()
            return original_call(instance, name, args, timeout)

        output = self.root / "interrupted"
        with mock.patch.object(TableSources, "call", new=interrupt_read):
            with self.assertRaises(KeyboardInterrupt):
                table_assessment_run.run(
                    self.protocol_path, self.questions_path, self.corpus, output
                )
        report = json.loads((output / "report.json").read_text())
        self.assertEqual(report["run_status"], "interrupted")
        self.assertEqual(report["task_denominator"], 2)
        self.assertEqual([case["status"] for case in report["cases"]], ["interrupted", "pending"])
        self.assertEqual(len(report["cases"][0]["trace"]), 1)

    def test_gold_and_extra_fields_are_rejected_before_construction(self):
        invalid_cases = [
            {
                "id": "one",
                "source_id": "first-source",
                "question": "needle",
                "answer": "10",
                "table_id": "table-1",
                "row_indices": [5],
            }
        ]
        self.write_inputs(invalid_cases)
        output = self.root / "output"
        with mock.patch.object(
            table_assessment_run, "TableSources", side_effect=AssertionError("constructed")
        ) as constructor:
            with self.assertRaisesRegex(ValueError, "fields must be exact"):
                table_assessment_run.run(
                    self.protocol_path, self.questions_path, self.corpus, output
                )
        constructor.assert_not_called()
        self.assertFalse(output.exists())

    def test_duplicate_unknown_and_nonlexical_cases_are_rejected(self):
        invalid_sets = [
            [
                {"id": "same", "source_id": "first-source", "question": "needle"},
                {"id": "same", "source_id": "second-source", "question": "café"},
            ],
            [{"id": "one", "source_id": "unknown", "question": "needle"}],
            [{"id": "one", "source_id": "first-source", "question": "---"}],
        ]
        for index, cases in enumerate(invalid_sets):
            with self.subTest(index=index):
                self.write_inputs(cases)
                with self.assertRaises(ValueError):
                    table_assessment_run.run(
                        self.protocol_path,
                        self.questions_path,
                        self.corpus,
                        self.root / f"output-{index}",
                    )

    def test_question_manifest_and_runtime_hash_mismatches_are_rejected(self):
        cases = [{"id": "one", "source_id": "first-source", "question": "needle"}]
        overrides = [
            {"questions_sha256": "0" * 64},
            {"corpus_manifest_sha256": "0" * 64},
            {"runtime_sha256": "0" * 64},
        ]
        for index, override in enumerate(overrides):
            with self.subTest(override=override):
                self.write_inputs(cases, **override)
                with mock.patch.object(table_assessment_run.TableSources, "call") as call:
                    with self.assertRaisesRegex(ValueError, "SHA-256"):
                        table_assessment_run.run(
                            self.protocol_path,
                            self.questions_path,
                            self.corpus,
                            self.root / f"mismatch-{index}",
                        )
                call.assert_not_called()

    def test_no_hit_and_read_error_are_retained_as_completed_observations(self):
        cases = [
            {"id": "miss", "source_id": "first-source", "question": "absenttoken"},
            {"id": "read-error", "source_id": "first-source", "question": "needle"},
        ]
        self.write_inputs(cases)
        original_call = TableSources.call

        def fail_only_read(instance, name, args, timeout):
            if name == "read_table":
                return {"error": "targeted read failure"}
            return original_call(instance, name, args, timeout)

        with mock.patch.object(TableSources, "call", new=fail_only_read):
            report = table_assessment_run.run(
                self.protocol_path, self.questions_path, self.corpus, self.root / "output"
            )

        self.assertEqual([case["status"] for case in report["cases"]], ["no_hit", "read_error"])
        self.assertEqual([len(case["trace"]) for case in report["cases"]], [1, 2])
        self.assertEqual(report["status_counts"]["no_hit"], 1)
        self.assertEqual(report["status_counts"]["read_error"], 1)
        self.assertEqual(sum(report["status_counts"].values()), 2)
        error_trace = report["cases"][1]["trace"][1]
        self.assertEqual(
            error_trace["response_canonical_sha256"],
            digest(canonical({"error": "targeted read failure"}).encode("utf-8")),
        )

    def test_existing_output_is_rejected_without_mutation(self):
        cases = [{"id": "one", "source_id": "first-source", "question": "needle"}]
        self.write_inputs(cases)
        output = self.root / "output"
        output.mkdir()
        marker = output / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already exists"):
            table_assessment_run.run(self.protocol_path, self.questions_path, self.corpus, output)
        self.assertEqual(marker.read_text(), "keep")
        self.assertFalse((output / "report.json").exists())

    def test_unexpected_interruption_persists_failed_and_pending_cases(self):
        cases = [
            {"id": "done", "source_id": "first-source", "question": "needle"},
            {"id": "broken", "source_id": "first-source", "question": "explode"},
            {"id": "later", "source_id": "second-source", "question": "café"},
        ]
        self.write_inputs(cases)
        original_call = TableSources.call

        def interrupt(instance, name, args, timeout):
            if name == "search_tables" and args["query"] == "explode":
                raise RuntimeError("unexpected " + "x" * 2000)
            return original_call(instance, name, args, timeout)

        output = self.root / "output"
        with mock.patch.object(TableSources, "call", new=interrupt):
            with self.assertRaisesRegex(RuntimeError, "unexpected"):
                table_assessment_run.run(
                    self.protocol_path, self.questions_path, self.corpus, output
                )

        persisted = json.loads((output / "report.json").read_text())
        self.assertEqual(
            [case["status"] for case in persisted["cases"]],
            ["completed", "failed", "pending"],
        )
        self.assertLessEqual(len(persisted["cases"][1]["error"]), 1000)
        self.assertEqual(persisted["status_counts"]["completed"], 1)
        self.assertEqual(persisted["status_counts"]["failed"], 1)
        self.assertEqual(persisted["status_counts"]["pending"], 1)

    def test_runtime_digest_covers_untracked_matching_files(self):
        extra = Path(table_assessment_run.__file__).with_name("temporary_digest_probe.py")
        before = table_assessment_run.runtime_digest()
        try:
            extra.write_text("VALUE = 1\n", encoding="utf-8")
            self.assertNotEqual(table_assessment_run.runtime_digest(), before)
        finally:
            extra.unlink(missing_ok=True)
        self.assertEqual(table_assessment_run.runtime_digest(), before)


if __name__ == "__main__":
    unittest.main()
