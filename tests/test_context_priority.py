import copy
import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from provenance.context import _omission, project_messages, tool_result_chars
from provenance.controls import LimitReached
from tests import test_context as context_tests

PATH = Path(__file__).resolve().parents[1] / "eval/reports/context-priority-2026-11-16/analyze.py"
spec = importlib.util.spec_from_file_location("context_priority_analysis", PATH)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class ContextPriorityTests(unittest.TestCase):
    def history(self):
        history = context_tests.pair("search", "s", {"results": []})
        for rank in range(1, 4):
            history += context_tests.pair(
                "read_source",
                f"r{rank}",
                {"id": "s", "locator": f"L{rank}", "lines": [{"line": rank, "text": 'é\\"' * 150}]},
            )
        return history

    def test_only_optional_priority_changes_and_history_is_immutable(self):
        history = self.history()
        original = copy.deepcopy(history)
        expected = copy.deepcopy(history)
        expected[5] = _omission(expected[5])
        limit = tool_result_chars(expected)
        baseline = project_messages(history, max_tool_result_chars=limit)
        challenger = analysis.project_messages(history, max_tool_result_chars=limit)
        self.assertTrue(json.loads(baseline[3]["output"])["omitted_from_model_context"])
        self.assertEqual(baseline[5], history[5])
        self.assertEqual(challenger[3], history[3])
        self.assertTrue(json.loads(challenger[5]["output"])["omitted_from_model_context"])
        self.assertEqual(challenger[-1], history[-1])
        self.assertEqual(challenger[1], history[1])
        self.assertEqual(tool_result_chars(challenger), limit)
        self.assertEqual(history, original)
        self.assertEqual(analysis.baseline_projector, project_messages)

    def test_full_fit_and_old_search_omission_match_baseline(self):
        history = (
            context_tests.pair("search", "old", {"results": [{"snippet": "old"}]}) + self.history()
        )
        self.assertEqual(analysis.project_messages(history), project_messages(history))
        self.assertEqual(analysis.project_messages([]), [])

    def test_required_oversize_and_invalid_bounds_match_baseline(self):
        for policy in [project_messages, analysis.project_messages]:
            with self.assertRaisesRegex(LimitReached, "tool_context_size_limit"):
                policy(self.history(), max_tool_result_chars=100)
            for bound in [0, -1, True, 2.5]:
                with self.assertRaises(ValueError):
                    policy([], max_tool_result_chars=bound)

    def test_failed_latest_read_stays_required(self):
        history = self.history()
        history += context_tests.pair("read_source", "failed", {"error": "failure"})
        minimal = [dict(m) for m in history]
        for i in [3, 5, 7]:
            minimal[i] = _omission(minimal[i])
        result = analysis.project_messages(
            history, max_tool_result_chars=tool_result_chars(minimal)
        )
        self.assertEqual(result[-1], history[-1])
        for i in [3, 5, 7]:
            self.assertTrue(json.loads(result[i]["output"])["omitted_from_model_context"])

    def test_override_is_local_restored_and_attribution_is_explicit(self):
        original_result = {"protocol_sha256": "input"}
        module = SimpleNamespace(
            project_messages=project_messages, execute=mock.Mock(return_value=original_result)
        )
        result = analysis._challenger(module, "outer", Path("unused"))
        self.assertIs(module.project_messages, project_messages)
        self.assertEqual(result["input_integrity_protocol_sha256"], "input")
        self.assertEqual(result["experiment_protocol_sha256"], "outer")
        self.assertNotIn("protocol_sha256", result)
        module.execute.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            analysis._challenger(module, "outer", Path("unused"))
        self.assertIs(module.project_messages, project_messages)
        module.project_messages = lambda x: x
        with self.assertRaisesRegex(ValueError, "Unexpected baseline"):
            analysis._challenger(module, "outer", Path("unused"))

    def test_outer_wrapper_binds_both_outputs_before_completion(self):
        import tempfile

        from eval.scripts.table_assessment_run import runtime_digest
        from provenance.evidence_coverage import digest

        for mutation in [None, "baseline", "challenger"]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                base = root / "base"
                base.mkdir()
                (base / "analyze.py").write_text("synthetic fixture")
                (base / "protocol.json").write_text("{}")
                historical = root / "historical.json"
                result = {
                    "protocol_sha256": "inner",
                    "cases": [
                        {
                            "id": "one",
                            "snapshots": {
                                f"top_{k}": {"component_coverage": {"complete": False}}
                                for k in [1, 3, 5]
                            },
                        }
                    ],
                }
                historical.write_text(json.dumps(result, indent=2) + "\n")
                protocol = root / "protocol.json"
                protocol.write_text(
                    json.dumps(
                        {
                            "version": "context-priority-protocol-v1",
                            "policy": analysis.POLICY,
                            "limit": 32000,
                            "analysis_sha256": digest(PATH),
                            "runtime_sha256": runtime_digest(),
                            "baseline_analysis_sha256": digest(base / "analyze.py"),
                            "baseline_protocol_sha256": digest(base / "protocol.json"),
                            "baseline_result_sha256": digest(historical),
                        }
                    )
                )
                output = root / "output"
                module = SimpleNamespace(project_messages=project_messages)

                def execute(
                    _protocol, path, result=result, module=module, mutation=mutation, output=output
                ):
                    value = copy.deepcopy(result)
                    if module.project_messages is analysis.project_messages:
                        for snapshot in value["cases"][0]["snapshots"].values():
                            snapshot["component_coverage"]["complete"] = True
                        if mutation == "baseline":
                            (output / "baseline.json").write_text("{}")
                    path.write_text(json.dumps(value, indent=2) + "\n")
                    return value

                module.execute = execute
                actual_write = analysis._write

                def write(path, value, actual_write=actual_write, mutation=mutation):
                    actual_write(path, value)
                    if mutation == "challenger" and path.name == "challenger.json":
                        path.write_text("{}")

                with (
                    mock.patch.multiple(analysis, BASE=base, BASE_RESULT=historical),
                    mock.patch.object(analysis, "_load_baseline", return_value=module),
                    mock.patch.object(analysis, "_write", side_effect=write),
                ):
                    if mutation:
                        with self.assertRaisesRegex(ValueError, "Condition output changed"):
                            analysis.execute(protocol, output)
                        self.assertEqual(
                            json.loads((output / "run.json").read_text())["status"], "aborted"
                        )
                    else:
                        state = analysis.execute(protocol, output)
                        self.assertEqual(state["status"], "complete")
                        self.assertEqual(
                            state["paired"]["top_5"], {"wins": 1, "losses": 0, "ties": 0}
                        )
                self.assertIs(module.project_messages, project_messages)
