import copy
import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock

from provenance.evidence_coverage import digest
from provenance.sources import Sources
from tests import test_context_comparison as comparison_tests

base = comparison_tests.module

PATH = (
    Path(__file__).resolve().parents[1] / "eval/assessments/financebench-compact-read-v1/assess.py"
)
spec = importlib.util.spec_from_file_location("compact_assessment", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CompactAssessmentTests(unittest.TestCase):
    def fixture(self):
        helper = comparison_tests.ContextComparisonTests()
        self.addCleanup(helper.doCleanups)
        root, old_protocol, history, historical_grade = helper.fixture()
        corpus = root / "corpus/sources.json"
        manifest = json.loads(corpus.read_text())
        for source in manifest["sources"]:
            source["line_locations"] = [{"page": n // 30 + 1} for n in range(120)]
            source["extraction"] = {
                "diagnostics_version": "pdf-extraction-diagnostics-v2",
                "page_count": 4,
                "text_completeness": "not_verified",
                "warnings": ["Synthetic uncertainty"],
                "pages": [
                    {"page": p, "emitted_line_start": (p - 1) * 30 + 1, "emitted_line_end": p * 30}
                    for p in range(1, 5)
                ],
            }
        corpus.write_text(json.dumps(manifest))
        packet = json.loads(base.PACKETS.read_text())
        packet["corpus_manifest_sha256"] = digest(corpus)
        base.PACKETS.write_text(json.dumps(packet))
        old = json.loads(old_protocol.read_text())
        old["files"] = {k: digest(p) for k, p in base._paths().items()}
        old_protocol.write_text(json.dumps(old))
        base.run(old_protocol, history)
        base.grade(old_protocol, history, historical_grade)
        here, old_base = root / "assessment", root / "base"
        here.mkdir()
        old_base.mkdir()
        (here / "plan.md").write_text("Synthetic protocol plan")
        (here / "inner-protocol.json").write_bytes(old_protocol.read_bytes() + b"\n")
        (old_base / "comparison-protocol.json").write_bytes(old_protocol.read_bytes())
        for name, value in [
            ("HERE", here),
            ("BASE", old_base),
            ("HISTORY", history),
            ("HISTORICAL_GRADE", historical_grade),
        ]:
            patch = mock.patch.object(module, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        patch = mock.patch.object(module, "_base", return_value=base)
        patch.start()
        self.addCleanup(patch.stop)
        protocol = here / "protocol.json"
        self.freeze(protocol)
        return root, protocol, root / "experiment", root / "grades"

    def freeze(self, protocol):
        protocol.write_text(
            json.dumps(
                {
                    "version": "compact-read-assessment-v1",
                    "modes": module.MODES,
                    "runtime_sha256": module.runtime_digest(),
                    "files": {k: digest(p) for k, p in module._paths().items()},
                }
            )
        )

    def test_both_modes_replay_with_explicit_attribution_and_unchanged_evidence(self):
        root, protocol, run_dir, output = self.fixture()
        state = module.run(protocol, run_dir)
        self.assertEqual(state["status"], "complete")
        self.assertEqual(
            state["historical_default_compatibility"], "exact_except_new_protocol_hash"
        )
        result = module.grade(protocol, run_dir, output)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["protocol_sha256"], digest(protocol))
        self.assertTrue(all(c["selected_denominator"] == 6 for c in result["conditions"].values()))
        self.assertEqual(
            result["metadata_paired"][base.POLICIES[0]]["top_5"],
            {"wins": 0, "losses": 0, "ties": 6},
        )
        self.assertIs(base.Sources, Sources)

    def test_default_mismatch_prevents_compact_dispatch(self):
        root, protocol, run_dir, output = self.fixture()
        path = module.HISTORY / "run.json"
        historical = json.loads(path.read_text())
        historical["cases"][0]["search"]["mode"] = "different frozen historical result"
        path.write_text(json.dumps(historical))
        self.freeze(protocol)
        with self.assertRaisesRegex(ValueError, "Default run differs"):
            module.run(protocol, run_dir)
        state = json.loads((run_dir / "run.json").read_text())
        self.assertEqual(state["status"], "aborted")
        self.assertEqual(state["modes"][module.MODES[1]]["status"], "pending")
        self.assertFalse((run_dir / module.MODES[1]).exists())

    def test_compact_search_mismatch_stops_before_reads(self):
        root, protocol, run_dir, output = self.fixture()
        original = Sources.search

        def changed(self, *args, **kwargs):
            result = original(self, *args, **kwargs)
            if self.read_extraction_version == module.MODES[1]:
                result["mode"] = "mismatch"
            return result

        with mock.patch.object(Sources, "search", changed):
            with self.assertRaisesRegex(ValueError, "before read dispatch"):
                module.run(protocol, run_dir)
        compact = run_dir / module.MODES[1]
        state = json.loads((compact / "run.json").read_text())
        self.assertEqual(state["status"], "aborted")
        self.assertEqual(len(state["cases"]), 6)
        self.assertEqual(list(compact.glob("*.jsonl")), [])
        self.assertIs(base.Sources, Sources)

    def test_only_declared_metadata_projection_is_allowed(self):
        root, protocol, run_dir, output = self.fixture()
        module.run(protocol, run_dir)
        full, compact = [
            json.loads((run_dir / mode / "run.json").read_text()) for mode in module.MODES
        ]
        for change in [
            lambda r: r["lines"][0].update(text="different evidence"),
            lambda r: r["extraction"].update(warnings=[]),
            lambda r: r["extraction"]["read_projection"].update(full_diagnostics_sha256="0" * 64),
        ]:
            altered = copy.deepcopy(compact)
            change(altered["cases"][0]["reads"]["records"][0]["response"])
            with self.assertRaises(ValueError):
                module._same_evidence(full, altered)

    def test_immediate_run_or_grade_file_replacement_cannot_complete(self):
        root, protocol, run_dir, output = self.fixture()
        original_run = base.run
        calls = 0

        def corrupt_run(*args):
            nonlocal calls
            result = original_run(*args)
            calls += 1
            if calls == 2:
                (Path(args[1]) / "run.json").write_text("{}")
            return result

        with mock.patch.object(base, "run", side_effect=corrupt_run):
            with self.assertRaisesRegex(ValueError, "Written assessment output changed"):
                module.run(protocol, run_dir)
        self.assertEqual(json.loads((run_dir / "run.json").read_text())["status"], "aborted")
        valid = root / "valid"
        module.run(protocol, valid)
        original_grade = base.grade

        def corrupt_grade(*args):
            result = original_grade(*args)
            Path(args[2]).write_text("{}")
            return result

        with mock.patch.object(base, "grade", side_effect=corrupt_grade):
            with self.assertRaisesRegex(ValueError, "Written assessment output changed"):
                module.grade(protocol, valid, output)
        self.assertEqual(json.loads((output / "summary.json").read_text())["status"], "aborted")

    def test_boolean_counts_cannot_alias_integer_metadata_or_budgets(self):
        root, protocol, run_dir, output = self.fixture()
        module.run(protocol, run_dir)
        full, compact = [
            json.loads((run_dir / mode / "run.json").read_text()) for mode in module.MODES
        ]
        altered = copy.deepcopy(compact)
        altered["cases"][0]["reads"]["records"][0]["response"]["extraction"]["read_projection"][
            "retained_page_count"
        ] = True
        with self.assertRaisesRegex(ValueError, "provenance differ"):
            module._same_evidence(full, altered)
        altered = copy.deepcopy(compact)
        altered["cases"][0]["reads"]["budgets"]["top_1"]["attempted_reads"] = True
        with self.assertRaisesRegex(ValueError, "Evidence budget changed"):
            module._same_evidence(full, altered)

        altered = copy.deepcopy(compact)
        altered["cases"][0]["reads"]["budgets"].pop("top_5")
        with self.assertRaisesRegex(ValueError, "budget prefixes differ"):
            module._same_evidence(full, altered)

    def test_constructor_override_restores_on_interrupt(self):
        root, protocol, run_dir, output = self.fixture()
        with self.assertRaises(KeyboardInterrupt):
            with module._mode(module.MODES[1]):
                self.assertIsNot(base.Sources, Sources)
                raise KeyboardInterrupt
        self.assertIs(base.Sources, Sources)

    def test_output_mutation_and_run_inventory_are_rejected(self):
        root, protocol, run_dir, output = self.fixture()
        module.run(protocol, run_dir)
        (run_dir / "extra.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "incomplete or changed"):
            module.grade(protocol, run_dir, output)
        (run_dir / "extra.json").unlink()
        original = base.grade
        calls = 0

        def corrupt(*args):
            nonlocal calls
            result = original(*args)
            calls += 1
            if calls == 2:
                path = output / f"{module.MODES[0]}.json"
                path.write_bytes(path.read_bytes() + b" ")
            return result

        with mock.patch.object(base, "grade", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "Grade outputs changed"):
                module.grade(protocol, run_dir, output)
        self.assertEqual(json.loads((output / "summary.json").read_text())["status"], "aborted")


if __name__ == "__main__":
    unittest.main()
