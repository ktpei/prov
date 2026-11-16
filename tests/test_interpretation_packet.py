import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from provenance.evidence_coverage import digest

PATH = (
    Path(__file__).resolve().parents[1]
    / "eval/assessments/financebench-evidence-audit-v1/prepare_interpretation.py"
)
spec = importlib.util.spec_from_file_location("interpretation_packet", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InterpretationPacketTests(unittest.TestCase):
    def inputs(self):
        return [
            {
                "id": f"task-{i}",
                "question": f"Literal question {i}?",
                "context": {"doc_name": f"source-{i}", "answer": "SECRET"},
                "reference": "SECRET",
                "score": "SECRET",
            }
            for i in range(6)
        ]

    def test_allowlist_deterministic_and_exact_question_preservation(self):
        inputs = self.inputs()
        questions, custody = module.project(inputs)
        self.assertEqual((questions, custody), module.project(inputs))
        self.assertNotIn("SECRET", json.dumps(questions))
        self.assertEqual(set(questions), {"stage", "cases"})
        self.assertEqual(
            [c["case_id"] for c in questions["cases"]], [f"Q{i:02d}" for i in range(1, 7)]
        )
        for question, mapping in zip(questions["cases"], custody["mapping"], strict=True):
            self.assertEqual(set(question), {"case_id", "question"})
            self.assertEqual(question["question"], inputs[mapping["original_index"]]["question"])
            self.assertNotIn("task-", json.dumps(question))
            self.assertNotIn("source-", json.dumps(question))

    def fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        inputs = root / "inputs.json"
        inputs.write_text(json.dumps(self.inputs()))
        for name in ["plan.md", "reviewer-instructions.md"]:
            (root / name).write_text("Synthetic instructions")
        patch = mock.patch.multiple(module, HERE=root, INPUTS=inputs, EXPECTED=digest(inputs))
        patch.start()
        self.addCleanup(patch.stop)
        return root

    def test_receipt_binds_same_inputs_and_outputs_and_rejects_overwrite(self):
        root = self.fixture()
        receipt = module.prepare()
        self.assertEqual(receipt["inputs"]["inputs"], digest(root / "inputs.json"))
        for name, expected in receipt["outputs"].items():
            self.assertEqual(expected, digest(root / "stage-1" / name))
        with self.assertRaises(FileExistsError):
            module.prepare()

    def test_mid_projection_input_mutation_rejected_without_packet(self):
        root = self.fixture()
        original = module.project

        def mutate(inputs):
            (root / "plan.md").write_text("Changed")
            return original(inputs)

        with mock.patch.object(module, "project", side_effect=mutate):
            with self.assertRaisesRegex(ValueError, "input changed"):
                module.prepare()
        self.assertFalse((root / "stage-1").exists())

    def test_later_write_cannot_corrupt_already_checked_question_packet(self):
        root = self.fixture()
        original = Path.write_bytes

        def write(path, data):
            result = original(path, data)
            if path.name == "custodian.json":
                original(path.parent / "questions.json", b"{}")
            return result

        with mock.patch.object(Path, "write_bytes", write):
            with self.assertRaisesRegex(ValueError, "Final reviewer packet"):
                module.prepare()
        self.assertTrue((root / "stage-1").exists())

    def test_bad_denominator_duplicate_or_blank_question_rejected(self):
        for kind in ["count", "duplicate", "blank"]:
            inputs = self.inputs()
            if kind == "count":
                inputs.pop()
            elif kind == "duplicate":
                inputs[1]["id"] = inputs[0]["id"]
            else:
                inputs[0]["question"] = " "
            with self.assertRaises(ValueError):
                module.project(inputs)
