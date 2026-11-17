import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PATH = (
    Path(__file__).resolve().parents[1]
    / "eval/assessments/financebench-evidence-audit-v1/validate_evidence_review.py"
)
spec = importlib.util.spec_from_file_location("evidence_review_validation", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EvidenceReviewValidationTests(unittest.TestCase):
    def fixture(self):
        packets, cases, hashes = [], [], {}
        for n in range(1, 7):
            cid, sid = f"Q{n:02d}", f"source-{n}"
            hashes[f"{cid}.json"] = f"hash-{n}"
            lines = [
                {"line": i, "text": text}
                for i, text in enumerate(
                    ["Assets 10", "Revenue 20", "Review-only qualification", "Other 5"], 1
                )
            ]
            packets.append(
                {
                    "case_id": cid,
                    "source": {"id": sid},
                    "excerpts": [
                        {"evidence_id": "E1", "lines": lines[:1]},
                        {"evidence_id": "E2", "lines": lines[1:2]},
                        {"evidence_id": "E3", "lines": lines[3:]},
                    ],
                    "review_only_pages": [{"lines": lines}],
                    "interpretations": [
                        {"id": "I01", "required_facts": [{"id": "R1"}, {"id": "R2"}]}
                    ],
                }
            )
            citations = [
                {
                    "source_id": sid,
                    "start_line": 1,
                    "end_line": 2,
                    "text_quote": "Assets 10\nRevenue 20",
                    "evidence_ids": ["E1", "E2"],
                    "review_only_context": False,
                },
                {
                    "source_id": sid,
                    "start_line": 3,
                    "end_line": 3,
                    "text_quote": "Review-only qualification",
                    "evidence_ids": [],
                    "review_only_context": True,
                },
            ]
            requirements = [
                {
                    "requirement_id": f"R{i}",
                    "status": "supported",
                    "reason": "Synthetic evidence",
                    "spans": [citation],
                }
                for i, citation in enumerate(citations, 1)
            ]
            evidence_set = {
                "id": "S1",
                "requirements": {
                    r["requirement_id"]: copy.deepcopy(r["spans"]) for r in requirements
                },
                "assumptions": [],
                "uses_review_only_context": True,
            }
            cases.append(
                {
                    "case_id": cid,
                    "source_uncertainty": [],
                    "interpretations": [
                        {
                            "interpretation_id": "I01",
                            "requirements": requirements,
                            "complete_evidence_sets": [evidence_set],
                            "unresolved_issues": [],
                            "proposed_rubric_revisions": [],
                        }
                    ],
                }
            )
        return (
            {
                "stage": "masked_evidence_review",
                "reviewer": "synthetic",
                "input_sha256": hashes,
                "cases": cases,
                "outside_access": [],
                "recognition_or_prior_knowledge": "none",
            },
            packets,
            hashes,
        )

    def file_fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "stage-2/reviewer").mkdir(parents=True)
        instruction = root / "evidence-review-instructions.md"
        instruction.write_text("synthetic instructions")
        review, packets, _ = self.fixture()
        hashes = {}
        for packet in packets:
            path = root / "stage-2/reviewer" / f"{packet['case_id']}.json"
            path.write_text(json.dumps(packet))
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        review["input_sha256"] = hashes
        path = root / "review.json"
        path.write_text(json.dumps(review))
        receipt = root / "stage-2/receipt.json"
        receipt.write_text(
            json.dumps(
                {
                    "inputs": {
                        "instructions": hashlib.sha256(instruction.read_bytes()).hexdigest()
                    },
                    "outputs": {f"reviewer/{name}": sha for name, sha in hashes.items()},
                }
            )
        )
        patch = mock.patch.multiple(
            module, HERE=root, RECEIPT_SHA=hashlib.sha256(receipt.read_bytes()).hexdigest()
        )
        patch.start()
        self.addCleanup(patch.stop)
        return root, path

    def test_file_receipt_instruction_packet_and_snapshot_binding(self):
        root, path = self.file_fixture()
        result = module.validate_file(path)
        self.assertEqual(result["review_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        for name, message in [
            ("stage-2/receipt.json", "receipt"),
            ("evidence-review-instructions.md", "instructions"),
            ("stage-2/reviewer/Q01.json", "packet"),
        ]:
            with self.subTest(name=name):
                target = root / name
                original = target.read_bytes()
                target.write_text("changed")
                with self.assertRaisesRegex(ValueError, message):
                    module.validate_file(path)
                target.write_bytes(original)
        original_validate = module.validate

        def mutate(*args):
            result = original_validate(*args)
            path.write_text("changed late")
            return result

        with mock.patch.object(module, "validate", side_effect=mutate):
            with self.assertRaisesRegex(ValueError, "inputs changed"):
                module.validate_file(path)

    def test_disclosure_shapes_preserved_without_inferring_blinding(self):
        for disclosure in [[], "No outside access", {"access": "none"}]:
            review, packets, hashes = self.fixture()
            review["outside_access"] = disclosure
            self.assertEqual(
                module.validate(review, packets, hashes)["outside_access_disclosed"], disclosure
            )

    def test_literal_union_and_review_only_context_pass_without_semantic_claim(self):
        result = module.validate(*self.fixture())
        self.assertEqual(
            result["counts"],
            {
                "cases": 6,
                "interpretations": 6,
                "requirements": 12,
                "complete_sets": 6,
                "citations": 24,
                "review_only_citations": 12,
            },
        )
        self.assertEqual(result["financial_sufficiency"], "not_validated")

    def test_forged_quote_wrong_source_boolean_bound_and_missing_line_reject(self):
        for problem in ["quote", "source", "bool", "outside"]:
            with self.subTest(problem=problem):
                review, packets, hashes = self.fixture()
                citation = review["cases"][0]["interpretations"][0]["requirements"][0]["spans"][0]
                if problem == "quote":
                    citation["text_quote"] = "Assets 999"
                elif problem == "source":
                    citation["source_id"] = "other"
                elif problem == "bool":
                    citation["start_line"] = True
                else:
                    citation["end_line"] = 5
                with self.assertRaises(ValueError):
                    module.validate(review, packets, hashes)

    def test_review_only_flags_cannot_fill_gap_or_hide_page_context(self):
        for problem in ["span_flag", "set_flag", "missing_excerpt", "unrelated_excerpt"]:
            with self.subTest(problem=problem):
                review, packets, hashes = self.fixture()
                interpretation = review["cases"][0]["interpretations"][0]
                if problem == "span_flag":
                    interpretation["requirements"][1]["spans"][0]["review_only_context"] = False
                elif problem == "set_flag":
                    interpretation["complete_evidence_sets"][0]["uses_review_only_context"] = False
                elif problem == "missing_excerpt":
                    interpretation["requirements"][0]["spans"][0]["evidence_ids"] = ["E1"]
                else:
                    interpretation["requirements"][0]["spans"][0]["evidence_ids"].append("E3")
                with self.assertRaises(ValueError):
                    module.validate(review, packets, hashes)

    def test_case_interpretation_requirement_and_hash_boundaries(self):
        for problem in ["case", "interpretation", "requirement", "hash", "conditional"]:
            with self.subTest(problem=problem):
                review, packets, hashes = self.fixture()
                interpretation = review["cases"][0]["interpretations"][0]
                if problem == "case":
                    review["cases"].pop()
                elif problem == "interpretation":
                    interpretation["interpretation_id"] = "I99"
                elif problem == "requirement":
                    interpretation["complete_evidence_sets"][0]["requirements"].pop("R2")
                elif problem == "hash":
                    review["input_sha256"] = {}
                else:
                    interpretation["requirements"][0]["status"] = "conditional"
                with self.assertRaises(ValueError):
                    module.validate(review, packets, hashes)
