import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from langgraph.checkpoint.sqlite import SqliteSaver

from provenance.agent import run
from provenance.evaluation import validate_report_evidence
from provenance.graph import run_graph
from provenance.model import ReplayModel
from provenance.sources import Sources
from tests import test_graph as graph_tests


class ReadModeIntegrationTests(unittest.TestCase):
    def setUp(self):
        helper = graph_tests.GraphTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        self.root = helper.root
        text = "Revenue FY2024: 120 USD million.\nSecond page note.\n"
        (self.root / "acme.txt").write_text(text)
        manifest = json.loads((self.root / "sources.json").read_text())
        source = manifest["sources"][0]
        source.update(
            sha256=hashlib.sha256(text.encode()).hexdigest(),
            line_locations=[{"page": 1}, {"page": 2}],
            extraction={
                "diagnostics_version": "pdf-extraction-diagnostics-v2",
                "page_count": 2,
                "warning_count": 1,
                "warnings": ["Page 2 geometry uncertain"],
                "text_completeness": "not_verified",
                "pages": [
                    {"page": 1, "emitted_line_start": 1, "emitted_line_end": 1},
                    {"page": 2, "emitted_line_start": 2, "emitted_line_end": 2},
                ],
            },
        )
        (self.root / "sources.json").write_text(json.dumps(manifest))

    def sources(self, mode="full-v1"):
        return Sources(self.root, read_extraction_version=mode)

    def test_both_engines_record_mode_and_grader_replays_it(self):
        task = {"question": "Revenue?", "source_ids": ["acme"]}
        for engine in [run, run_graph]:
            with self.subTest(engine=engine.__name__):
                compact = engine(
                    "Revenue?",
                    ReplayModel([graph_tests.read(), graph_tests.answer()]),
                    self.sources("pdf-returned-pages-v1"),
                )
                self.assertEqual(compact["status"], "completed")
                self.assertEqual(
                    compact["events"][0]["read_extraction_version"], "pdf-returned-pages-v1"
                )
                validate_report_evidence(task, compact, directory=self.root)
                tampered = copy.deepcopy(compact)
                tampered["events"][0]["read_extraction_version"] = "full-v1"
                with self.assertRaisesRegex(ValueError, "Tool result differs"):
                    validate_report_evidence(task, tampered, directory=self.root)
                typed = copy.deepcopy(compact)
                result_event = next(e for e in typed["events"] if e["event"] == "tool_result")
                result_event["result"]["extraction"]["read_projection"]["retained_page_count"] = (
                    True
                )
                with self.assertRaisesRegex(ValueError, "Tool result differs"):
                    validate_report_evidence(task, typed, directory=self.root)
                full = engine(
                    "Revenue?",
                    ReplayModel([graph_tests.read(), graph_tests.answer()]),
                    self.sources(),
                )
                self.assertEqual(full["events"][0]["read_extraction_version"], "full-v1")
                full["events"][0].pop("read_extraction_version")
                validate_report_evidence(task, full, directory=self.root)

    def test_resume_rejects_mode_change_before_model_calls(self):
        options = {"checkpoint_path": self.root / "checkpoint.db", "thread_id": "compact"}
        first = run_graph(
            "Revenue?",
            ReplayModel([graph_tests.read()]),
            self.sources("pdf-returned-pages-v1"),
            pause_after_tools=True,
            **options,
        )
        self.assertEqual(first["status"], "paused")
        wrong = ReplayModel([graph_tests.answer()])
        with mock.patch.object(wrong, "step", wraps=wrong.step) as step:
            with self.assertRaisesRegex(ValueError, "read-format differs"):
                run_graph("Revenue?", wrong, self.sources(), resume=True, **options)
            step.assert_not_called()
        resumed = run_graph(
            "Revenue?",
            ReplayModel([graph_tests.answer()]),
            self.sources("pdf-returned-pages-v1"),
            resume=True,
            **options,
        )
        self.assertEqual(resumed["status"], "completed")
        validate_report_evidence(
            {"question": "Revenue?", "source_ids": ["acme"]}, resumed, directory=self.root
        )

        cached_wrong = ReplayModel([])
        with mock.patch.object(cached_wrong, "step", wraps=cached_wrong.step) as step:
            with self.assertRaisesRegex(ValueError, "read-format differs"):
                run_graph("Revenue?", cached_wrong, self.sources(), resume=True, **options)
            step.assert_not_called()

    def test_legacy_checkpoint_without_mode_means_full_metadata(self):
        checkpoint = self.root / "legacy.db"
        options = {"checkpoint_path": checkpoint, "thread_id": "legacy"}
        first = run_graph(
            "Revenue?",
            ReplayModel([graph_tests.read()]),
            self.sources(),
            pause_after_tools=True,
            **options,
        )
        self.assertEqual(first["status"], "paused")
        config = {"configurable": {"thread_id": "legacy", "checkpoint_ns": ""}}
        with SqliteSaver.from_conn_string(str(checkpoint)) as saver:
            saved = saver.get_tuple(config)
            legacy = copy.deepcopy(saved.checkpoint)
            legacy["channel_values"]["identity"].pop("read_extraction_version")
            legacy["channel_values"]["events"][0].pop("read_extraction_version")
            kind, data = saver.serde.dumps_typed(legacy)
            saver.conn.execute(
                "UPDATE checkpoints SET type=?, checkpoint=? WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=?",
                (kind, data, "legacy", "", legacy["id"]),
            )
            saver.conn.commit()
        with self.assertRaisesRegex(ValueError, "read-format differs"):
            run_graph(
                "Revenue?",
                ReplayModel([]),
                self.sources("pdf-returned-pages-v1"),
                resume=True,
                **options,
            )
        resumed = run_graph(
            "Revenue?", ReplayModel([graph_tests.answer()]), self.sources(), resume=True, **options
        )
        self.assertEqual(resumed["status"], "completed")
        validate_report_evidence(
            {"question": "Revenue?", "source_ids": ["acme"]}, resumed, directory=self.root
        )

    def test_cli_supports_explicit_mode_for_both_engines_and_rejects_unknown_mode(self):
        root = Path(__file__).resolve().parents[1]
        for engine in ["custom", "langgraph"]:
            command = [
                sys.executable,
                "-m",
                "provenance",
                "demo",
                "--engine",
                engine,
                "--read-extraction-version",
                "pdf-returned-pages-v1",
            ]
            result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                report["events"][0]["read_extraction_version"], "pdf-returned-pages-v1"
            )
        invalid = subprocess.run(
            [sys.executable, "-m", "provenance", "demo", "--read-extraction-version", "unknown"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("invalid choice", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
