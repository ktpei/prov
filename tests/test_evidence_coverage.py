import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from eval.scripts.table_assessment_run import runtime_digest
from provenance.benchmarks import canonical_hash
from provenance.evidence_coverage import coverage, digest, grade
from provenance.source_quality import evaluate_corpus
from tests import test_source_quality as quality_tests


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


class EvidenceCoverageTests(unittest.TestCase):
    def setUp(self):
        self.source = SimpleNamespace(
            documents={"s": {"text": "Header\n17\nOther header\n23\nQualification\n"}}
        )
        self.case = {
            "id": "q",
            "source_id": "s",
            "disposition": "mapped",
            "reason": "",
            "required_components": ["header", "value"],
            "alternatives": [{"header": [[1, 1]], "value": [[2, 2]]}],
        }

    def row(self, *ranges):
        lines = self.source.documents["s"]["text"].splitlines()
        return {
            "id": "q",
            "retrieved_hits": [
                {
                    "source_id": "s",
                    "start_line": a,
                    "end_line": b,
                    "snippet_locator": f"L{a}-L{b}",
                    "snippet": "\n".join(lines[a - 1 : b]),
                }
                for a, b in ranges
            ],
        }

    def test_union_requires_all_components_and_single_hit_is_separate(self):
        result = coverage([self.case], [self.row((1, 1), (2, 2))], self.source)[0]["coverage"][
            "returned_snippets"
        ]
        self.assertFalse(result["top_1"]["complete"])
        self.assertTrue(result["top_3"]["complete"])
        self.assertFalse(result["top_3"]["single_hit_complete"])

    def test_partial_alternatives_cannot_be_combined(self):
        self.case["alternatives"].append({"header": [[3, 3]], "value": [[4, 4]]})
        result = coverage([self.case], [self.row((1, 1), (4, 4))], self.source)[0]["coverage"][
            "returned_snippets"
        ]
        self.assertFalse(result["top_5"]["complete"])
        self.case["alternatives"][0].pop("value")
        with self.assertRaisesRegex(ValueError, "every required component"):
            coverage([self.case], [self.row((1, 4))], self.source)

    def test_empty_fallback_and_partial_text_never_count_as_complete_snippet(self):
        row = self.row((1, 2))
        row["retrieved_hits"][0]["snippet"] = ""
        result = coverage([self.case], [row], self.source)[0]["coverage"]
        self.assertTrue(result["parent_passage_opportunity"]["top_1"]["complete"])
        self.assertFalse(result["returned_snippets"]["top_1"]["complete"])
        for text in ["Header", "Header\n18"]:
            row["retrieved_hits"][0]["snippet"] = text
            with self.assertRaisesRegex(ValueError, "exact parent source slice"):
                coverage([self.case], [row], self.source)
        row = self.row((2, 2))
        row["retrieved_hits"][0].update(snippet="Header", snippet_locator="L1")
        with self.assertRaisesRegex(ValueError, "exact parent source slice"):
            coverage([self.case], [row], self.source)

    def test_ineligible_packets_and_invalid_ranges_cannot_pass(self):
        case = {
            **self.case,
            "disposition": "unresolved",
            "reason": "Unmapped qualification",
            "alternatives": [],
        }
        result = coverage([case], [self.row((1, 5))], self.source)[0]
        self.assertFalse(result["coverage"]["returned_snippets"]["top_5"]["complete"])
        for bad in [[True, 2], [1, 99], [2, 1]]:
            self.case["alternatives"][0]["value"] = [bad]
            with self.assertRaises(ValueError):
                coverage([self.case], [self.row((1, 5))], self.source)
        with self.assertRaisesRegex(ValueError, "order and denominator"):
            coverage([], [self.row((1, 2))], self.source)

    def fixture(self):
        helper = quality_tests.SourceQualityTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        bundle = quality_tests._bundle(
            [quality_tests._task("one", "needle", [helper.evidence(0, "needle 17")])]
        )
        corpus = helper.corpus(
            bundle, lines=["Header USD 2025", "needle 17", "qualification"], pages=[1, 1, 1]
        )
        prepared = helper.root / "prepared"
        prepared.mkdir()
        for key, value in bundle.items():
            write(prepared / (key + ".json"), value)
        report = helper.root / "report.json"
        write(report, evaluate_corpus(bundle, corpus, source_scope="declared_document"))
        source = json.loads((corpus / "sources.json").read_text())["sources"][0]
        packets = helper.root / "packets.json"
        case = copy.deepcopy(self.case)
        case.update(id="one", source_id="REPORT")
        write(
            packets,
            {
                "version": "pdf-evidence-components-v1",
                "corpus_manifest_sha256": digest(corpus / "sources.json"),
                "sources": {"REPORT": {k: source[k] for k in ["original_sha256", "sha256"]}},
                "cases": [case],
            },
        )
        protocol = helper.root / "protocol.json"
        write(
            protocol,
            {
                "version": "pdf-evidence-coverage-protocol-v1",
                "report_sha256": digest(report),
                "packets_sha256": digest(packets),
                "corpus_manifest_sha256": digest(corpus / "sources.json"),
                "prepared_sha256": canonical_hash(bundle["manifest"]),
                "prepared_files_sha256": {
                    name: digest(prepared / name)
                    for name in ["manifest.json", "tasks.json", "inputs.json"]
                },
                "corpus_binding_sha256": digest(corpus / "benchmark_binding.json"),
                "runtime_sha256": runtime_digest(),
            },
        )
        return protocol, prepared, corpus, report, packets, helper.root / "grade.json"

    def test_end_to_end_replays_before_labels_and_distinguishes_opportunity(self):
        args = self.fixture()
        replayed = False
        original_read = Path.read_bytes

        def read(path):
            if path == args[4] and not replayed:
                raise AssertionError("Labels opened before replay")
            return original_read(path)

        def replay(*a, **kw):
            nonlocal replayed
            result = evaluate_corpus(*a, **kw)
            replayed = True
            return result

        with (
            mock.patch.object(Path, "read_bytes", new=read),
            mock.patch("provenance.evidence_coverage.evaluate_corpus", side_effect=replay),
        ):
            result = grade(*args)
        self.assertEqual(result["selected_denominator"], 1)
        self.assertEqual(result["summary"]["parent_passage_opportunity"]["top_5_complete_count"], 1)
        self.assertEqual(result["summary"]["returned_snippets"]["top_5_complete_count"], 0)
        with self.assertRaisesRegex(ValueError, "already exists"):
            grade(*args)

    def test_forged_report_fails_replay_even_with_updated_report_digest(self):
        args = self.fixture()
        report = json.loads(args[3].read_text())
        report["tasks"][0]["retrieved_hits"][0]["snippet_locator"] = "L1-L3"
        write(args[3], report)
        protocol = json.loads(args[0].read_text())
        protocol["report_sha256"] = digest(args[3])
        write(args[0], protocol)
        with self.assertRaisesRegex(ValueError, "replay exactly"):
            grade(*args)
        self.assertFalse(args[5].exists())

    def test_post_replay_input_mutations_reject_output(self):
        for name in ["manifest.json", "tasks.json", "inputs.json", "benchmark_binding.json"]:
            with self.subTest(name=name):
                args = self.fixture()
                target = (args[2] if name == "benchmark_binding.json" else args[1]) / name

                def replay(*a, target=target, **kw):
                    result = evaluate_corpus(*a, **kw)
                    target.write_bytes(target.read_bytes() + b"\n")
                    return result

                with mock.patch("provenance.evidence_coverage.evaluate_corpus", side_effect=replay):
                    with self.assertRaisesRegex(ValueError, "frozen identity mismatch"):
                        grade(*args)
                self.assertFalse(args[5].exists())
