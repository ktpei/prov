import copy
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import test_context_comparison as fixtures

from provenance.benchmarks import canonical_hash
from provenance.evidence_coverage import digest
from provenance.sources import Sources

PATH = (
    Path(__file__).resolve().parents[1] / "eval/assessments/financebench-page-ranking-v1/assess.py"
)
spec = importlib.util.spec_from_file_location("page_ranking_assessment", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PageRankingAssessmentTests(unittest.TestCase):
    def fixture(self, width=10, fact_line=1):
        root, _, _, _ = fixtures.ContextComparisonTests.fixture(self, width=width)
        base = fixtures.module
        manifest = json.loads((base.CORPUS / "sources.json").read_bytes())
        for source in manifest["sources"]:
            source["line_locations"] = [{"page": i // 20 + 1} for i in range(120)]
            source["extraction"] = {"page_count": 6}
        fixtures.write(base.CORPUS / "sources.json", manifest)
        packets = json.loads(base.PACKETS.read_bytes())
        packets["corpus_manifest_sha256"] = digest(base.CORPUS / "sources.json")
        for case in packets["cases"]:
            case["alternatives"] = [{"fact": [[fact_line, fact_line]]}]
        fixtures.write(base.PACKETS, packets)
        ids = [c["id"] for c in packets["cases"]]
        history = root / "history"
        with mock.patch.object(base, "_freeze", return_value=({"case_ids": ids}, lambda: None)):
            base.run(root / "protocol.json", history)
        paths = {
            **base._paths(),
            "wrapper": PATH,
            **{f"history/{p.name}": p for p in history.iterdir()},
        }
        for key, value in [
            ("_base", lambda: base),
            ("_paths", lambda: paths),
            ("HISTORY", history),
            ("HISTORY_PROTOCOL", root / "protocol.json"),
            ("_environment", lambda: {"synthetic": True}),
        ]:
            patch = mock.patch.object(module, key, value)
            patch.start()
            self.addCleanup(patch.stop)
        protocol = root / "page-protocol.json"
        fixtures.write(
            protocol,
            {
                "version": "page-ranking-assessment-v1",
                "parameters": module.PARAMETERS,
                "environment": {"synthetic": True},
                "case_ids": ids,
                "runtime_sha256": module.runtime_digest(),
                "files": {k: digest(p) for k, p in paths.items()},
            },
        )
        return root, protocol, root / "page-run", root / "page-grade.json"

    def test_collection_whole_replay_and_grading(self):
        _, protocol, run_dir, output = self.fixture()
        with mock.patch.object(
            module, "compare_page_ranking", wraps=module.compare_page_ranking
        ) as ranking:
            state = module.run(protocol, run_dir)
            self.assertEqual(ranking.call_count, 6)
        self.assertEqual(state["status"], "complete")
        result = module.grade(protocol, run_dir, output)
        self.assertTrue(result["replay_verified"])
        self.assertEqual(result["selected_denominator"], 6)
        self.assertEqual(len(result["pool_25"]), 6)
        self.assertEqual(result["operations"]["derived_search_responses"], 12)
        for branch in result["branches"].values():
            self.assertEqual(branch["operations"]["read_attempts"], 30)
        self.assertEqual(canonical_hash(result), canonical_hash(json.loads(output.read_bytes())))

    def test_mutated_candidate_rejected_before_packet_parse_even_with_rehashed_receipt(self):
        _, protocol, run_dir, output = self.fixture()
        module.run(protocol, run_dir)
        path = run_dir / "deterministic/run.json"
        state = json.loads(path.read_bytes())
        state["cases"][0]["ranking"]["candidates"][0]["page_rank"] = 999
        fixtures.write(path, state)
        receipt = json.loads((run_dir / "receipt.json").read_bytes())
        receipt["deterministic"] = module._inventory(run_dir / "deterministic")
        fixtures.write(run_dir / "receipt.json", receipt)
        original = module._load_object

        def load(raw, label):
            if label == "Page ranking packets":
                self.fail("Packets opened before mismatched replay rejected")
            return original(raw, label)

        with mock.patch.object(module, "_load_object", side_effect=load):
            with self.assertRaisesRegex(ValueError, "replay exactly"):
                module.grade(protocol, run_dir, output)
        self.assertFalse(output.exists())

    def test_returned_replay_object_must_match_written_artifact_before_labels(self):
        _, protocol, run_dir, output = self.fixture()
        module.run(protocol, run_dir)
        original_run, original_load = module.run, module._load_object

        def mutate_return(*args):
            state = copy.deepcopy(original_run(*args))
            state["cases"][0]["ranking"]["candidates"] = []
            return state

        def load(raw, label):
            if label == "Page ranking packets":
                self.fail("Packet parse preceded replay object binding")
            return original_load(raw, label)

        with (
            mock.patch.object(module, "run", side_effect=mutate_return),
            mock.patch.object(module, "_load_object", side_effect=load),
        ):
            with self.assertRaisesRegex(ValueError, "returned object"):
                module.grade(protocol, run_dir, output)
        self.assertFalse(output.exists())

    def test_failed_reads_keep_slots_and_never_receive_delivery_credit(self):
        with mock.patch.object(Sources, "read", side_effect=ValueError("synthetic unavailable")):
            _, protocol, run_dir, output = self.fixture()
            module.run(protocol, run_dir)
            result = module.grade(protocol, run_dir, output)
        for branch in result["branches"].values():
            self.assertEqual(branch["operations"]["failed_reads"], 30)
            for case in branch["read"]:
                self.assertFalse(case["coverage"]["returned_snippets"]["top_5"]["complete"])
            for policy in branch["conditions"].values():
                self.assertTrue(all(row["complete_count"] == 0 for row in policy.values()))

    def test_truncated_parent_does_not_credit_unreturned_boundary_line(self):
        _, protocol, run_dir, output = self.fixture(width=1200, fact_line=20)
        module.run(protocol, run_dir)
        result = module.grade(protocol, run_dir, output)
        for branch in result["branches"].values():
            self.assertEqual(branch["operations"]["truncated_reads"], 30)
            for case in branch["read"]:
                self.assertTrue(case["coverage"]["parent_passage_opportunity"]["top_1"]["complete"])
                self.assertFalse(case["coverage"]["returned_snippets"]["top_5"]["complete"])

    def test_timing_is_separate_but_bound_and_extra_files_rejected(self):
        _, protocol, run_dir, output = self.fixture()
        module.run(protocol, run_dir)
        (run_dir / "telemetry.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "receipt binding"):
            module.grade(protocol, run_dir, output)
        (run_dir / "extra").write_text("unexpected")
        with self.assertRaisesRegex(ValueError, "inventory"):
            module.grade(protocol, run_dir, output)

    def test_interruption_keeps_six_slots_and_no_success_receipt(self):
        _, protocol, run_dir, output = self.fixture()
        with mock.patch.object(
            module, "compare_page_ranking", side_effect=RuntimeError("synthetic failure")
        ):
            with self.assertRaises(RuntimeError):
                module.run(protocol, run_dir)
        state = json.loads((run_dir / "deterministic/run.json").read_bytes())
        self.assertEqual(state["status"], "aborted")
        self.assertEqual(len(state["cases"]), 6)
        self.assertEqual(sum(c["status"] == "pending" for c in state["cases"]), 5)
        self.assertFalse((run_dir / "receipt.json").exists())
        self.assertFalse(output.exists())

    def test_challenger_failure_preserves_control_and_full_replay_before_labels(self):
        _, protocol, run_dir, output = self.fixture()
        original_reader = module.read_ranked_passages

        def read(sources, hits, journal):
            if "challenger" in str(journal):
                with mock.patch.object(
                    sources, "read", side_effect=ValueError("synthetic failure")
                ):
                    return original_reader(sources, hits, journal)
            return original_reader(sources, hits, journal)

        with mock.patch.object(module, "read_ranked_passages", side_effect=read):
            module.run(protocol, run_dir)
        original_load = module._load_object
        with mock.patch.object(module, "read_ranked_passages", side_effect=read) as reader:

            def load(raw, label):
                if label == "Page ranking packets":
                    self.assertEqual(reader.call_count, 12)
                return original_load(raw, label)

            with mock.patch.object(module, "_load_object", side_effect=load):
                result = module.grade(protocol, run_dir, output)
        self.assertEqual(result["branches"]["control"]["operations"]["failed_reads"], 0)
        self.assertEqual(result["branches"]["challenger"]["operations"]["failed_reads"], 30)
        self.assertEqual(result["selected_denominator"], 6)

    def test_telemetry_write_mutation_prevents_success_receipt(self):
        _, protocol, run_dir, _ = self.fixture()
        original_write = module._write

        def write(path, value):
            if Path(path).name == "telemetry.json":
                value = copy.deepcopy(value)
                value["cases"][0]["ranking_seconds"] = -1
            original_write(path, value)

        with mock.patch.object(module, "_write", side_effect=write):
            with self.assertRaisesRegex(ValueError, "returned object"):
                module.run(protocol, run_dir)
        self.assertFalse((run_dir / "receipt.json").exists())

    def test_startup_hash_seed_required(self):
        code = f"import runpy; runpy.run_path({str(PATH)!r})['_environment']()"
        for seed, expected in [("0", 0), ("1", 1)]:
            result = subprocess.run(
                [sys.executable, "-c", code],
                env={**os.environ, "PYTHONHASHSEED": seed},
                capture_output=True,
            )
            self.assertEqual(result.returncode, expected)

    def test_pool_exact_union_and_alternative_isolation(self):
        self.fixture()
        source = Sources(fixtures.module.CORPUS)
        case = json.loads(fixtures.module.PACKETS.read_bytes())["cases"][0]

        def measure(ranges, alternatives):
            case["required_components"] = list(alternatives[0])
            case["alternatives"] = alternatives
            rows = [
                {
                    "id": case["id"],
                    "retrieved_hits": [
                        {
                            "source_id": case["source_id"],
                            "start_line": a,
                            "end_line": b,
                            "snippet": "",
                        }
                        for a, b in ranges
                    ],
                }
            ]
            return module.pool_coverage([case], rows, source)[0]

        self.assertFalse(measure([(1, 2), (4, 5)], [{"fact": [[2, 4]]}])["complete"])
        self.assertTrue(measure([(1, 1), (10, 10)], [{"fact": [[1, 1], [10, 10]]}])["complete"])
        self.assertFalse(
            measure(
                [(1, 1), (10, 10)],
                [{"a": [[1, 1]], "b": [[8, 8]]}, {"a": [[3, 3]], "b": [[10, 10]]}],
            )["complete"]
        )
        self.assertTrue(measure([(n, n) for n in range(1, 26)], [{"fact": [[25, 25]]}])["complete"])
        for ranges in [
            [(True, 2)],
            [(2, 1)],
            [(1, 121)],
            [(1, 1)] * 2,
            [(n, n) for n in range(1, 27)],
        ]:
            with self.assertRaises(ValueError):
                measure(ranges, [{"fact": [[1, 1]]}])
