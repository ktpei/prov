"""Failure-oriented checks for full-document benchmark reporting."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from provenance.agent import run
from provenance.evaluation import evaluate_packet, grade_packet_answer
from provenance.model import ReplayModel
from provenance.sources import Sources


class PacketEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        text = "\n".join(["Generic front matter"] * 50 + ["Revenue 430.1 million in Q3 2024"])
        digest = hashlib.sha256(text.encode()).hexdigest()
        (self.directory / "source.txt").write_text(text)
        (self.directory / "sources.json").write_text(
            json.dumps(
                {
                    "sources": [
                        {
                            "id": "release",
                            "text_file": "source.txt",
                            "sha256": digest,
                            "title": "Release",
                        }
                    ]
                }
            )
        )
        self.task = {
            "id": "revenue",
            "category": "numerical",
            "question": "What was revenue?",
            "queries": ["revenue"],
            "answerable": True,
            "evidence": [{"source_id": "release", "patterns": [r"430\.1", "Q3 2024"]}],
            "numeric_claims": [
                {
                    "key": "revenue",
                    "value": 430.1,
                    "tolerance": 0,
                    "unit": "USD million",
                    "period": "Q3 2024",
                }
            ],
            "rubric": "Verify revenue, units, period, source support, and extra claims.",
        }
        self.benchmark_path = self.directory / "benchmark.json"
        self.benchmark_path.write_text(
            json.dumps(
                {"version": "test", "source_hashes": {"release": digest}, "tasks": [self.task]}
            )
        )

    def test_retrieval_miss_is_separate_from_extraction_success(self):
        with patch(
            "provenance.sources.Sources.search",
            return_value={"results": [{"id": "release", "start_line": 1, "end_line": 10}]},
        ):
            report = evaluate_packet(self.directory, self.benchmark_path)
        row = report["tasks"][0]
        self.assertTrue(row["extraction_anchors_passed"])
        self.assertFalse(row["retrieval_anchors_passed"])
        self.assertEqual(report["summary"]["model_calls"], 0)
        self.assertEqual(row["answer_quality"], "not_measured_no_model_called")

    def test_hash_change_requires_benchmark_review(self):
        benchmark = json.loads(self.benchmark_path.read_text())
        benchmark["source_hashes"]["release"] = "0" * 64
        self.benchmark_path.write_text(json.dumps(benchmark))
        with self.assertRaisesRegex(ValueError, "source hashes differ"):
            evaluate_packet(self.directory, self.benchmark_path)

    def test_missing_evidence_does_not_count_as_verified_abstention(self):
        benchmark = json.loads(self.benchmark_path.read_text())
        benchmark["tasks"][0].update(answerable=False, evidence=[])
        self.benchmark_path.write_text(json.dumps(benchmark))
        report = evaluate_packet(self.directory, self.benchmark_path)
        self.assertEqual(report["summary"]["evidence_tasks"], 0)
        self.assertIsNone(report["tasks"][0]["retrieval_anchors_passed"])
        self.assertEqual(
            report["tasks"][0]["abstention_quality"], "requires_model_run_and_semantic_review"
        )

    def test_consistent_custom_corpus_trace_passes_without_claiming_semantic_success(self):
        answer = {
            "answerable": True,
            "answer": "Revenue was 430.1 USD million in Q3 2024.",
            "claims": [
                {
                    "key": "revenue",
                    "value": 430.1,
                    "unit": "USD million",
                    "period": "Q3 2024",
                    "citations": [
                        {
                            "source_id": "release",
                            "locator": "L51",
                            "quote": "Revenue 430.1 million in Q3 2024",
                        }
                    ],
                }
            ],
        }
        responses = [
            {
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "read",
                        "name": "read_source",
                        "arguments": json.dumps(
                            {"source_id": "release", "start_line": 51, "end_line": 51}
                        ),
                    }
                ],
            },
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(answer)}],
                    }
                ],
            },
        ]
        report = run(self.task["question"], ReplayModel(responses), Sources(self.directory))
        result = grade_packet_answer(self.task, report, directory=self.directory)
        self.assertTrue(result["mechanical_checks_passed"])
        self.assertEqual(result["semantic_answer_quality"], "requires_human_review")
        event = next(event for event in report["events"] if event["event"] == "tool_result")
        event["result"]["lines"][0]["text"] = "Revenue 999 million"
        invalid = grade_packet_answer(self.task, report, directory=self.directory)
        self.assertFalse(invalid["trace_and_quote_checks_passed"])

    def test_number_with_wrong_unit_fails_and_missing_trace_is_not_trusted(self):
        report = {
            "mode": "fake",
            "answer": {
                "answerable": True,
                "claims": [
                    {"value": 430.1, "unit": "USD billion", "period": "Q3 2024", "citations": []}
                ],
            },
        }
        result = grade_packet_answer(self.task, report, directory=self.directory)
        self.assertFalse(result["trace_and_quote_checks_passed"])
        self.assertFalse(result["numeric_claim_checks"][0]["passed"])
        self.assertFalse(result["mechanical_checks_passed"])
        self.assertEqual(result["semantic_answer_quality"], "requires_human_review")


if __name__ == "__main__":
    unittest.main()
