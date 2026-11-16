import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from provenance.context import project_messages
from provenance.evidence_coverage import digest
from provenance.sources import Sources

PATH = Path(__file__).resolve().parents[1] / "eval/assessments/financebench-context-v1/compare.py"
spec = importlib.util.spec_from_file_location("context_comparison", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


class ContextComparisonTests(unittest.TestCase):
    def fixture(self, width=10):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        corpus, prepared = root / "corpus", root / "prepared"
        corpus.mkdir()
        docs, inputs, cases = [], [], []
        for i in range(6):
            sid, tid = f"s{i}", f"task{i}"
            original = corpus / f"{sid}.pdf"
            original.write_bytes(b"synthetic original")
            text = corpus / f"{sid}.txt"
            text.write_text("\n".join(f"inventory {n} " + "x" * width for n in range(120)) + "\n")
            docs.append(
                {
                    "id": sid,
                    "title": sid,
                    "text_file": text.name,
                    "sha256": digest(text),
                    "original_file": original.name,
                    "original_sha256": digest(original),
                }
            )
            inputs.append({"id": tid, "question": "inventory", "context": {"doc_name": sid}})
            cases.append(
                {
                    "id": tid,
                    "source_id": sid,
                    "disposition": "mapped",
                    "reason": "synthetic",
                    "required_components": ["fact"],
                    "alternatives": [{"fact": [[1, 1]]}],
                }
            )
        write(corpus / "sources.json", {"sources": docs})
        write(prepared / "inputs.json", inputs)
        packets = root / "packets.json"
        write(
            packets,
            {
                "version": "pdf-evidence-components-v1",
                "corpus_manifest_sha256": digest(corpus / "sources.json"),
                "sources": {
                    s["id"]: {k: s[k] for k in ["sha256", "original_sha256"]} for s in docs
                },
                "cases": cases,
            },
        )
        paths = {
            "inputs": prepared / "inputs.json",
            "corpus": corpus / "sources.json",
            "packets": packets,
            "driver": PATH,
            "baseline": module.BASE,
            "challenger": module.CHALLENGER,
        }
        for name, value in [("PREPARED", prepared), ("CORPUS", corpus), ("PACKETS", packets)]:
            patch = mock.patch.object(module, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        patch = mock.patch.object(module, "_paths", return_value=paths)
        patch.start()
        self.addCleanup(patch.stop)
        protocol = root / "protocol.json"
        write(
            protocol,
            {
                "version": "financebench-context-comparison-v1",
                "limit": 32000,
                "policies": module.POLICIES,
                "case_ids": [t["id"] for t in inputs],
                "runtime_sha256": module.runtime_digest(),
                "files": {n: digest(p) for n, p in paths.items()},
            },
        )
        return root, protocol, root / "run", root / "grade.json"

    def test_run_is_label_free_and_replay_precedes_labels(self):
        root, protocol, run_dir, output = self.fixture()
        original_load = module._load_object
        original_run = module.run
        original_search, original_read = Sources.search, Sources.read
        calls = {"search": 0, "read": 0}
        replayed = False

        def search(self, *args, **kwargs):
            calls["search"] += 1
            return original_search(self, *args, **kwargs)

        def read(self, *args, **kwargs):
            calls["read"] += 1
            return original_read(self, *args, **kwargs)

        def load(raw, label):
            if label == "Comparison packets":
                self.assertTrue(replayed)
            return original_load(raw, label)

        def replay(*args):
            nonlocal replayed
            result = original_run(*args)
            replayed = True
            return result

        with (
            mock.patch.object(Sources, "search", search),
            mock.patch.object(Sources, "read", read),
            mock.patch.object(module, "_load_object", side_effect=load),
        ):
            result = module.run(protocol, run_dir)
            self.assertEqual(calls, {"search": 6, "read": 30})
            self.assertEqual(result["status"], "complete")
            with mock.patch.object(module, "run", side_effect=replay):
                graded = module.grade(protocol, run_dir, output)
        self.assertEqual(calls, {"search": 12, "read": 60})
        self.assertEqual(graded["selected_denominator"], 6)
        self.assertEqual(graded["paired"]["top_5"], {"wins": 0, "losses": 0, "ties": 6})
        for case in result["cases"]:
            for k in ["top_1", "top_3", "top_5"]:
                self.assertEqual(
                    *(case["conditions"][p][k]["canonical_sha256"] for p in module.POLICIES)
                )

    def test_empty_search_and_failed_first_slots_keep_denominator(self):
        root, protocol, run_dir, output = self.fixture()
        with mock.patch.object(
            Sources, "search", return_value={"results": [], "mode": "frozen_corpus"}
        ):
            module.run(protocol, run_dir)
            result = module.grade(protocol, run_dir, output)
        self.assertEqual(result["operations"]["read_attempts"], 0)
        self.assertEqual(result["selected_denominator"], 6)
        self.assertTrue(
            all(result["conditions"][p]["top_5"]["complete_count"] == 0 for p in module.POLICIES)
        )
        original_read = Sources.read

        def fail_first(self, sid, start, end, timeout):
            if start == 1:
                raise ValueError("synthetic failed slot")
            return original_read(self, sid, start, end, timeout)

        with mock.patch.object(Sources, "read", fail_first):
            saved = module.run(protocol, root / "failed")
            failed = module.grade(protocol, root / "failed", root / "failed-grade.json")
        self.assertEqual(failed["operations"]["failed_reads"], 6)
        self.assertEqual(failed["operations"]["read_attempts"], 30)
        self.assertTrue(
            all(
                c["reads"]["records"][0]["rank"] == 1
                and c["reads"]["records"][0]["status"] == "failed"
                for c in saved["cases"]
            )
        )

    def test_interrupt_persists_six_slots_and_original_search(self):
        root, protocol, run_dir, output = self.fixture()
        with mock.patch.object(module, "read_ranked_passages", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                module.run(protocol, run_dir)
        state = json.loads((run_dir / "run.json").read_text())
        self.assertEqual(state["status"], "aborted")
        self.assertEqual(len(state["cases"]), 6)
        self.assertEqual(state["cases"][0]["status"], "search_saved")
        self.assertIn("search", state["cases"][0])
        self.assertTrue(all(c["status"] == "pending" for c in state["cases"][1:]))

    def test_mutated_run_journal_inventory_or_inputs_rejected_before_labels(self):
        root, protocol, run_dir, output = self.fixture()
        module.run(protocol, run_dir)
        files = {p: p.read_bytes() for p in run_dir.iterdir()}
        original_load = module._load_object

        def no_packets(raw, label):
            self.assertNotEqual(label, "Comparison packets")
            return original_load(raw, label)

        for target in [run_dir / "run.json", run_dir / "case-0.jsonl", run_dir / "extra.json"]:
            target.write_bytes(target.read_bytes() + b" " if target.exists() else b"{}")
            with mock.patch.object(module, "_load_object", side_effect=no_packets):
                with self.assertRaisesRegex(ValueError, "replay exactly"):
                    module.grade(protocol, run_dir, output)
            if target in files:
                target.write_bytes(files[target])
            else:
                target.unlink()
        (root / "prepared/inputs.json").write_text("[]")
        with self.assertRaisesRegex(ValueError, "frozen file"):
            module.grade(protocol, run_dir, output)

    def test_policy_override_restored_on_interruption_and_bad_ranks_rejected(self):
        baseline = SimpleNamespace(project_messages=project_messages)
        calls = 0

        def snapshots(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt
            return {"top_1": {"canonical_sha256": "same"}}

        baseline.snapshots = snapshots
        with self.assertRaises(KeyboardInterrupt):
            module._project(baseline, SimpleNamespace(project_messages=lambda x: x), "q", {}, [])
        self.assertIs(baseline.project_messages, project_messages)
        with self.assertRaisesRegex(ValueError, "ordered"):
            module._project(baseline, None, "q", {}, [{"rank": 2, "status": "failed"}])

    def test_oversized_required_search_blocks_all_prefixes_without_evidence(self):
        root, protocol, run_dir, output = self.fixture()
        search = {"results": [], "mode": "frozen_corpus", "synthetic_oversize": "x" * 33000}
        with mock.patch.object(Sources, "search", return_value=search):
            module.run(protocol, run_dir)
            graded = module.grade(protocol, run_dir, output)
        for policy in module.POLICIES:
            for key in ["top_1", "top_3", "top_5"]:
                self.assertEqual(graded["conditions"][policy][key]["blocked_count"], 6)
                self.assertEqual(graded["conditions"][policy][key]["complete_count"], 0)

    def test_post_replay_journal_mutation_is_rejected(self):
        root, protocol, run_dir, output = self.fixture()
        module.run(protocol, run_dir)
        original = module._load_object

        def mutate(raw, label):
            value = original(raw, label)
            if label == "Comparison packets":
                with (run_dir / "case-0.jsonl").open("a") as handle:
                    handle.write(" ")
            return value

        with mock.patch.object(module, "_load_object", side_effect=mutate):
            with self.assertRaisesRegex(ValueError, "Grading inputs changed"):
                module.grade(protocol, run_dir, output)
        self.assertFalse(output.exists())

    def test_written_run_mutation_is_rejected_and_search_failure_is_durable(self):
        root, protocol, run_dir, output = self.fixture()
        original = module._write

        def corrupt(path, value):
            original(path, value)
            if value["status"] == "complete":
                path.write_bytes(path.read_bytes() + b" ")

        with mock.patch.object(module, "_write", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "Execution output changed"):
                module.run(protocol, run_dir)
        self.assertEqual(json.loads((run_dir / "run.json").read_text())["status"], "aborted")
        with mock.patch.object(
            Sources, "search", side_effect=RuntimeError("synthetic search failure")
        ):
            with self.assertRaises(RuntimeError):
                module.run(protocol, root / "search-failure")
        state = json.loads((root / "search-failure/run.json").read_text())
        self.assertEqual(state["status"], "aborted")
        self.assertEqual(len(state["cases"]), 6)
        self.assertEqual(state["cases"][0]["status"], "search_started")
        self.assertNotIn("search", state["cases"][0])
        self.assertTrue(all(c["status"] == "pending" for c in state["cases"][1:]))

    def test_five_read_policies_can_diverge_without_changing_delivery(self):
        root, protocol, run_dir, output = self.fixture(width=300)
        run = module.run(protocol, run_dir)
        result = module.grade(protocol, run_dir, output)
        self.assertEqual(result["paired"]["top_5"], {"wins": 6, "losses": 0, "ties": 0})
        self.assertTrue(
            all(
                c["coverage"]["returned_snippets"]["top_5"]["complete"]
                for c in result["delivery"]["read"]
            )
        )
        for case in run["cases"]:
            for snapshots in case["conditions"].values():
                self.assertTrue(all(s["characters_after"] <= 32000 for s in snapshots.values()))


if __name__ == "__main__":
    unittest.main()
