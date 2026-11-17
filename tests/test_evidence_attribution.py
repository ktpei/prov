import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PATH = (
    Path(__file__).resolve().parents[1]
    / "eval/assessments/financebench-evidence-audit-v1/attribute_evidence.py"
)
spec = importlib.util.spec_from_file_location("evidence_attribution", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EvidenceAttributionTests(unittest.TestCase):
    def interpretation(self):
        return {
            "interpretation_id": "I1",
            "requirements": [{"requirement_id": "R1", "status": "supported"}],
            "complete_evidence_sets": [
                {
                    "id": "S1",
                    "requirements": {
                        "R1": [
                            {
                                "source_id": "s",
                                "start_line": 1,
                                "end_line": 3,
                                "review_only_context": True,
                            }
                        ]
                    },
                }
            ],
        }

    def test_exact_union_does_not_fill_gaps_or_cross_sources(self):
        i = self.interpretation()
        for lines in [{("s", 1), ("s", 3)}, {("other", 1), ("other", 2), ("other", 3)}]:
            self.assertFalse(module.assess_interpretation(i, lines)["any_set_covered"])
        # Review-only labels neither grant nor deny actual delivery.
        self.assertTrue(
            module.assess_interpretation(i, {("s", n) for n in (1, 2, 3)})["any_set_covered"]
        )

    def test_no_cross_set_mixing(self):
        i = self.interpretation()
        i["complete_evidence_sets"][0]["requirements"]["R2"] = [
            {"source_id": "s", "start_line": 10, "end_line": 10}
        ]
        alternative = copy.deepcopy(i["complete_evidence_sets"][0])
        alternative["id"] = "S2"
        alternative["requirements"]["R1"] = [{"source_id": "s", "start_line": 20, "end_line": 20}]
        alternative["requirements"]["R2"] = [{"source_id": "s", "start_line": 4, "end_line": 4}]
        i["complete_evidence_sets"].append(alternative)
        self.assertFalse(
            module.assess_interpretation(i, {("s", n) for n in (1, 2, 3, 4)})["any_set_covered"]
        )

    def test_absent_set_is_explicit_not_unanswerable(self):
        i = self.interpretation()
        i["complete_evidence_sets"] = []
        i["requirements"][0]["status"] = "conditional"
        result = module.assess_interpretation(i, {("s", n) for n in range(100)})
        self.assertEqual(result["disposition"], "no_adjudicated_complete_set")
        self.assertEqual(result["unresolved_requirements"], {"R1": "conditional"})
        self.assertFalse(result["any_set_covered"])

    def fixture(self):
        review = {"cases": [{"case_id": "Q1", "interpretations": [self.interpretation()]}]}
        mapping = {"mapping": [{"case_id": "Q1", "task_id": "task", "source_id": "s"}]}
        # Request tail is unreturned, second read fails, third fills the gap.
        records = [
            {
                "rank": 1,
                "status": "returned",
                "request": {"source_id": "s", "start_line": 1, "end_line": 99},
                "response": {"id": "s", "locator": "L1", "lines": [{"line": 1, "text": "one"}]},
            },
            {
                "rank": 2,
                "status": "failed",
                "request": {"source_id": "s", "start_line": 1, "end_line": 3},
            },
            {
                "rank": 3,
                "status": "returned",
                "request": {"source_id": "s", "start_line": 2, "end_line": 3},
                "response": {
                    "id": "s",
                    "locator": "L2-L3",
                    "lines": [{"line": 2, "text": "two"}, {"line": 3, "text": "three"}],
                },
            },
        ]
        branch = {
            "reads": {"records": records},
            "conditions": {
                policy: {
                    f"top_{k}": {
                        "retained_read_ranks": [1],
                        "read_hits": [
                            {
                                **r["request"],
                                "snippet": "one" if r["rank"] == 1 else "",
                                "snippet_locator": "L1"
                                if r["rank"] == 1
                                else f"L{r['request']['start_line']}",
                            }
                            for r in records[:k]
                        ],
                    }
                    for k in (1, 3, 5)
                }
                for policy in module.POLICIES
            },
        }
        run = {
            "cases": [
                {
                    "id": "task",
                    "source_id": "s",
                    "branches": {name: copy.deepcopy(branch) for name in ("control", "challenger")},
                }
            ]
        }
        return review, mapping, run

    def test_actual_delivery_retention_and_prefixes(self):
        result = module.attribute(*self.fixture())[0]["conditions"]
        self.assertEqual(len(result), 12)
        for key, measures in result.items():
            self.assertEqual(
                measures["delivered_reads"][0]["any_set_covered"], not key.endswith("top_1")
            )
            self.assertFalse(measures["retained_reads"][0]["any_set_covered"])

    def test_mapping_and_retention_fail_closed(self):
        review, mapping, run = self.fixture()
        run["cases"].append(copy.deepcopy(run["cases"][0]))
        with self.assertRaisesRegex(ValueError, "mapping"):
            module.attribute(review, mapping, run)
        review, mapping, run = self.fixture()
        run["cases"][0]["branches"]["control"]["conditions"][module.POLICIES[0]]["top_1"][
            "read_hits"
        ][0]["snippet_locator"] = "L1-L2"
        with self.assertRaisesRegex(ValueError, "snippet differs"):
            module.attribute(review, mapping, run)

    def test_file_gate_rejects_inventory_hash_and_lock_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            here = root / "audit"
            (here / "reviews").mkdir(parents=True)
            lock = here / "reviews/stage-2-lock.json"
            lock.write_text("{}\n")
            paths = {"audit/reviews/stage-2-lock.json": lock}
            protocol = root / "protocol.json"
            output = root / "result.json"
            value = {
                "version": "masked-evidence-attribution-protocol-v1",
                "files": {name: module.digest(path) for name, path in paths.items()},
            }
            with (
                mock.patch.object(module, "ROOT", root),
                mock.patch.object(module, "HERE", here),
                mock.patch.object(module, "input_paths", return_value=paths),
            ):
                protocol.write_text(json.dumps({**value, "files": {}}))
                with self.assertRaisesRegex(ValueError, "inventory"):
                    module.execute(protocol, output)
                protocol.write_text(json.dumps(value))
                lock.write_text('{"changed": true}\n')
                with self.assertRaisesRegex(ValueError, "input identity"):
                    module.execute(protocol, output)
                lock.write_text("{}\n")
                with self.assertRaisesRegex(ValueError, "lock identity"):
                    module.execute(protocol, output)
                self.assertFalse(output.exists())

    def test_omitted_failed_blocked_and_truncated_retention(self):
        _, _, run = self.fixture()
        branch = run["cases"][0]["branches"]["control"]
        records = branch["reads"]["records"]
        condition = branch["conditions"][module.POLICIES[0]]["top_3"]
        # Omitted rank 3 bounds lie entirely within delivered evidence but earn zero.
        # Failed rank 2 has a placeholder; rank 1 request tail extends to 99.
        self.assertEqual(module.retained_lines(records, condition), {("s", 1)})
        condition["retained_read_ranks"] = []
        condition["read_hits"][0]["snippet"] = ""
        condition["status"] = "blocked"
        self.assertEqual(module.retained_lines(records, condition), set())
        condition["retained_read_ranks"] = [2]
        with self.assertRaisesRegex(ValueError, "Failed read"):
            module.retained_lines(records, condition)

    def test_file_gate_never_overwrites_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            output.write_text("original")
            with self.assertRaisesRegex(ValueError, "already exists"):
                module.execute(Path(temporary) / "absent-protocol.json", output)
            self.assertEqual(output.read_text(), "original")
