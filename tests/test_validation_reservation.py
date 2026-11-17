import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from provenance.benchmarks import canonical_hash
from provenance.evidence_coverage import digest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "eval/assessments/financebench-page-validation-v1/reserve.py"
)
spec = importlib.util.spec_from_file_location("validation_reservation", SCRIPT)
reservation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reservation)


class ValidationReservationTests(unittest.TestCase):
    def fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        task_path = root / "runs/benchmark-data/financebench-public-v2/financebench-public.jsonl"
        doc_path = root / "runs/benchmark-data/financebench-documents/financebench-documents.jsonl"
        registry_path = root / "eval/development-exposures.json"
        for path in (task_path, doc_path, registry_path):
            path.parent.mkdir(parents=True, exist_ok=True)
        tasks, docs = [], []
        for n in range(30):
            name = f"company-{n}-10k"
            tasks.append(
                {
                    "financebench_id": f"id-{n}",
                    "doc_name": name,
                    "company": f"Company {n}",
                    "question": "DO NOT PROJECT",
                    "answer": "DO NOT PROJECT",
                }
            )
            docs.append(
                {
                    "doc_name": name,
                    "company": f"Company {n}",
                    "doc_type": "10k",
                    "doc_period": "2020",
                    "doc_link": "https://example.invalid",
                    "gics_sector": "UNUSED",
                }
            )
        task_path.write_text("\n".join(map(json.dumps, tasks)))
        doc_path.write_text("\n".join(map(json.dumps, docs)))
        registry_path.write_text(
            json.dumps({"groups": [{"group": "company-0-10k"}, {"group": "unknown-issuer"}]})
        )
        (root / "plan.md").write_text("Synthetic plan")
        return root, task_path, doc_path, registry_path

    def select(self, fixture):
        root, tasks, docs, _ = fixture
        with patch.multiple(
            reservation, ROOT=root, HERE=root, TASK_SHA=digest(tasks), DOC_SHA=digest(docs)
        ):
            return reservation.select()

    def test_replay_partition_exclusions_and_narrow_projection(self):
        fixture = self.fixture()
        result = self.select(fixture)
        self.assertEqual(result, self.select(fixture))
        selected = result["selected"]
        self.assertEqual(len(selected), 6)
        self.assertEqual(len({r["company"].casefold() for r in selected}), 6)
        self.assertNotIn("company-0-10k", [r["doc_name"] for r in selected])
        self.assertEqual(result["unresolved_exposed_groups"], ["unknown-issuer"])
        self.assertEqual(len(result["ledger"]), 30)
        for row in result["ledger"]:
            original_final = int(canonical_hash([17, row["doc_name"]])[:8], 16) % 5 == 0
            self.assertEqual(
                row["original_partition"], "internal_final" if original_final else "development"
            )
            if row["disposition"] == "selected":
                self.assertFalse(original_final)
        serialized = json.dumps(result)
        self.assertNotIn("DO NOT PROJECT", serialized)
        self.assertNotIn("UNUSED", serialized)
        self.assertEqual(result["registry_sha256"], digest(fixture[3]))

    def test_ambiguous_metadata_duplicate_ids_and_company_mismatch_fail(self):
        for problem in ("duplicate_doc", "duplicate_task", "company"):
            with self.subTest(problem=problem):
                fixture = self.fixture()
                _, task_path, doc_path, _ = fixture
                tasks = list(map(json.loads, task_path.read_text().splitlines()))
                docs = list(map(json.loads, doc_path.read_text().splitlines()))
                if problem == "duplicate_doc":
                    docs.append(docs[0])
                elif problem == "duplicate_task":
                    tasks.append(tasks[0])
                else:
                    tasks[0]["company"] = "Mismatched"
                task_path.write_text("\n".join(map(json.dumps, tasks)))
                doc_path.write_text("\n".join(map(json.dumps, docs)))
                with self.assertRaises(ValueError):
                    self.select(fixture)

    def test_known_aliases_and_insufficient_unique_companies(self):
        fixture = self.fixture()
        _, task_path, doc_path, registry_path = fixture
        tasks = list(map(json.loads, task_path.read_text().splitlines()))
        docs = list(map(json.loads, doc_path.read_text().splitlines()))
        for task, doc in zip(tasks, docs, strict=True):
            task["company"] = doc["company"] = "Marathon Oil"
        registry_path.write_text(json.dumps({"groups": [{"group": "MRO/2007"}]}))
        task_path.write_text("\n".join(map(json.dumps, tasks)))
        doc_path.write_text("\n".join(map(json.dumps, docs)))
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            self.select(fixture)

    def test_registry_change_during_selection_rejects_stale_exclusions(self):
        fixture = self.fixture()
        original = reservation.canonical_hash
        changed = False

        def mutate_once(value):
            nonlocal changed
            if not changed:
                changed = True
                fixture[3].write_text(json.dumps({"groups": []}))
            return original(value)

        with patch.object(reservation, "canonical_hash", side_effect=mutate_once):
            with self.assertRaisesRegex(ValueError, "input changed"):
                self.select(fixture)

    def test_input_identity_mismatch_fails_before_selection(self):
        fixture = self.fixture()
        with patch.multiple(
            reservation,
            ROOT=fixture[0],
            HERE=fixture[0],
            TASK_SHA="wrong",
            DOC_SHA=digest(fixture[2]),
        ):
            with self.assertRaisesRegex(ValueError, "Pinned data"):
                reservation.select()
