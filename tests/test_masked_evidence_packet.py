import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

PATH = (
    Path(__file__).resolve().parents[1]
    / "eval/assessments/financebench-evidence-audit-v1/prepare_evidence.py"
)
spec = importlib.util.spec_from_file_location("masked_evidence", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MaskedEvidencePacketTests(unittest.TestCase):
    def fixture(self):
        questions, mapping, rubrics, run, packets, documents = [], [], [], [], [], {}
        for i in range(6):
            cid, sid, tid = f"Q{i + 1:02d}", f"source-{i}", f"hidden-task-{i}"
            text = "Revenue 10\nCosts 5\nAssets 20\nReview context only"
            locations = [{"page": p} for p in [1, 1, 2, 2]]
            documents[sid] = {
                "id": sid,
                "text": text,
                "title": "Synthetic",
                "sha256": "text-hash",
                "original_sha256": "original-hash",
                "line_locations": locations,
                "extraction": {"page_count": 2},
            }
            questions.append({"case_id": cid, "question": "Literal finance question"})
            mapping.append({"case_id": cid, "task_id": tid, "source_id": sid})
            rubrics.append(
                {
                    "case_id": cid,
                    "interpretations": [
                        {
                            "id": "I01",
                            "description": "Explicit meaning",
                            "assumptions": [],
                            "unresolved_ambiguities": [],
                            "required_facts": [
                                {
                                    "id": "R01",
                                    "description": "Fact",
                                    "basis": "wording",
                                    "rationale": "needed",
                                }
                            ],
                            "reviewer_provenance": "MASKED_PROVENANCE",
                        }
                    ],
                }
            )
            response = {
                "id": sid,
                "sha256": "text-hash",
                "original_sha256": "original-hash",
                "locator": "L1-L2",
                "lines": [
                    {
                        "line": n,
                        "text": text.splitlines()[n - 1],
                        "original_location": locations[n - 1],
                    }
                    for n in [1, 2]
                ],
            }
            record = {
                "rank": 1,
                "status": "returned",
                "request": {"source_id": sid, "start_line": 1, "end_line": 4},
                "response": response,
            }
            run.append(
                {
                    "id": tid,
                    "source_id": sid,
                    "status": "complete",
                    "branches": {
                        b: {"reads": {"records": [copy.deepcopy(record)]}}
                        for b in ["control", "challenger"]
                    },
                }
            )
            packets.append(
                {"id": tid, "source_id": sid, "alternatives": [{"SECRET_ORIGINAL_ROLE": [[3, 3]]}]}
            )
        return (
            {"cases": questions},
            {"mapping": mapping},
            {"cases": rubrics},
            {"cases": run},
            {"cases": packets},
            SimpleNamespace(documents=documents),
        )

    def preparation_fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        data = self.fixture()
        for directory in ["stage-1", "reviews", "prepared", "run/deterministic", "experiment"]:
            (root / directory).mkdir(parents=True)

        def write(name, value):
            path = root / name
            path.write_text(json.dumps(value))
            return path

        write("stage-1/questions.json", data[0])
        write("stage-1/custodian.json", data[1])
        write("reviews/reconciliation-c.json", data[2])
        write("run/deterministic/run.json", data[3])
        packet = write("packets.json", data[4])
        for name in [
            "plan.md",
            "reviewer-instructions.md",
            "evidence-review-instructions.md",
            "prepare_interpretation.py",
            "prepared/inputs.json",
        ]:
            (root / name).write_text("synthetic frozen input")
        receipt = write(
            "stage-1/receipt.json",
            {
                "inputs": {
                    key: module.digest(root / name)
                    for key, name in {
                        "inputs": "prepared/inputs.json",
                        "plan": "plan.md",
                        "instructions": "reviewer-instructions.md",
                        "builder": "prepare_interpretation.py",
                    }.items()
                },
                "outputs": {
                    name: module.digest(root / "stage-1" / name)
                    for name in ["questions.json", "custodian.json"]
                },
            },
        )
        lock = write(
            "reviews/stage-1-lock.json",
            {
                "inputs": {
                    "reviews/reconciliation-c.json": module.digest(
                        root / "reviews/reconciliation-c.json"
                    )
                }
            },
        )
        inventory = {"synthetic": "bound"}
        grade = write("grade.json", {"replay_verified": True, "run_inventory": inventory})
        base = SimpleNamespace(PACKETS=packet, CORPUS=root / "corpus", PREPARED=root / "prepared")
        assessment = SimpleNamespace(
            _freeze=lambda path: ({}, lambda: None),
            _base=lambda: base,
            _validated_inventory=lambda *args: inventory,
        )
        patch = mock.patch.multiple(
            module,
            HERE=root,
            EXPERIMENT=root / "experiment",
            RUN=root / "run",
            GRADE=grade,
            LOCK_SHA=module.digest(lock),
            RECEIPT_SHA=module.digest(receipt),
            GRADE_SHA=module.digest(grade),
            _assessment=lambda: assessment,
            Sources=lambda path: data[5],
        )
        patch.start()
        self.addCleanup(patch.stop)
        return root

    def test_preparation_binds_every_output_and_receipt(self):
        root = self.preparation_fixture()
        result = module.prepare()
        self.assertEqual(result["cases"], 6)
        for name, expected in result["outputs"].items():
            self.assertEqual(module.digest(root / "stage-2" / name), expected)
        self.assertEqual(json.loads((root / "stage-2/receipt.json").read_bytes()), result)
        with self.assertRaises(FileExistsError):
            module.prepare()

    def test_changed_frozen_stage1_plan_fails_before_publication(self):
        root = self.preparation_fixture()
        (root / "plan.md").write_text("unauthorized scope drift")
        with self.assertRaisesRegex(ValueError, "stage-1 preparation dependency"):
            module.prepare()
        self.assertFalse((root / "stage-2").exists())

    def test_late_output_mutation_cannot_succeed(self):
        root = self.preparation_fixture()
        original = Path.open

        def open_file(path, *args, **kwargs):
            if path == root / "stage-2/receipt.json" and args == ("xb",):
                (root / "stage-2/reviewer/Q01.json").write_bytes(b"{}")
            return original(path, *args, **kwargs)

        with mock.patch.object(Path, "open", open_file):
            with self.assertRaisesRegex(ValueError, "Final masked evidence artifacts"):
                module.prepare()

    def test_dedup_allowlist_and_uniform_review_only_pages(self):
        data = self.fixture()
        reviewer, custody = module.assemble(*data)
        self.assertEqual((reviewer, custody), module.assemble(*data))
        self.assertEqual(len(reviewer), 6)
        packet = reviewer["Q01.json"]
        self.assertEqual(len(packet["excerpts"]), 2)
        self.assertEqual(
            {(e["start_line"], e["end_line"]) for e in packet["excerpts"]}, {(1, 2), (3, 3)}
        )
        self.assertEqual([p["page"] for p in packet["review_only_pages"]], [1, 2])
        self.assertTrue(all(p["review_only"] for p in packet["review_only_pages"]))
        self.assertEqual(packet["review_only_pages"][1]["lines"][-1]["text"], "Review context only")
        self.assertNotIn(4, {line["line"] for e in packet["excerpts"] for line in e["lines"]})
        encoded = json.dumps(reviewer)
        for hidden in [
            "SECRET_ORIGINAL_ROLE",
            "MASKED_PROVENANCE",
            "hidden-task",
            '"branch"',
            '"rank"',
            '"attribution"',
        ]:
            self.assertNotIn(hidden, encoded)
        self.assertEqual(sum(len(e["attribution"]) for e in custody["cases"][0]["excerpts"]), 3)

    def test_failed_read_is_recorded_only_in_custody(self):
        data = self.fixture()
        record = data[3]["cases"][0]["branches"]["control"]["reads"]["records"][0]
        record.update(status="failed", response=None)
        reviewer, custody = module.assemble(*data)
        self.assertEqual(custody["cases"][0]["failed_reads"], [{"branch": "control", "rank": 1}])
        self.assertNotIn('"failed_reads"', json.dumps(reviewer))
        self.assertEqual(len(reviewer["Q01.json"]["excerpts"]), 2)

    def test_changed_read_text_hash_range_or_rank_rejected(self):
        for problem in ["text", "hash", "range", "rank"]:
            with self.subTest(problem=problem):
                data = self.fixture()
                record = data[3]["cases"][0]["branches"]["control"]["reads"]["records"][0]
                if problem == "text":
                    record["response"]["lines"][0]["text"] = "changed"
                elif problem == "hash":
                    record["response"]["sha256"] = "changed"
                elif problem == "range":
                    record["request"]["end_line"] = 1
                else:
                    record["rank"] = True
                with self.assertRaises(ValueError):
                    module.assemble(*data)

    def test_page_mapping_and_case_alignment_rejected(self):
        for problem in [
            "bool_page",
            "unordered",
            "missing_page",
            "case_order",
            "denominator",
            "duplicate_run",
            "duplicate_control",
        ]:
            with self.subTest(problem=problem):
                data = self.fixture()
                source = data[-1].documents["source-0"]
                if problem == "bool_page":
                    source["line_locations"][0]["page"] = True
                elif problem == "unordered":
                    source["line_locations"] = list(reversed(source["line_locations"]))
                elif problem == "missing_page":
                    source["extraction"]["page_count"] = 3
                elif problem == "case_order":
                    data[2]["cases"].reverse()
                elif problem == "duplicate_run":
                    data[3]["cases"].append(copy.deepcopy(data[3]["cases"][0]))
                elif problem == "duplicate_control":
                    data[4]["cases"].append(copy.deepcopy(data[4]["cases"][0]))
                else:
                    data[3]["cases"].pop()
                with self.assertRaises(ValueError):
                    module.assemble(*data)
