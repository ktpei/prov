"""Synthetic offline tests for FinanceBench corpus source diagnostics."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from provenance.benchmarks import canonical_hash, prepare
from provenance.source_quality import evaluate_corpus
from provenance.sources import Sources


def _task(task_id, question, evidence, *, requires_review=False):
    reference = {
        "answer": "synthetic",
        "metric": "financebench_semantic_review",
        "evidence": evidence,
    }
    if requires_review:
        reference.update(
            requires_review="Unresolved synthetic annotation",
            reference_issues=["synthetic-unresolved"],
        )
    return {
        "id": task_id,
        "dataset": "financebench",
        "subset": "open_source",
        "source_split": "public",
        "question": question,
        "context": {},
        "metadata": {"doc_name": "REPORT"},
        "reference": reference,
    }


def _bundle(tasks):
    return prepare(
        tasks,
        source={
            "dataset": "financebench",
            "subset": "open_source",
            "source_split": "public",
            "url": "https://example.org/financebench",
            "revision": "a" * 40,
            "sha256": "b" * 64,
            "license": "synthetic",
        },
        count=len(tasks),
        seed=17,
        condition="full_agent",
        development_groups=sorted({task["metadata"]["doc_name"] for task in tasks}),
    )


class SourceQualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def corpus(self, bundle, *, lines=None, pages=None):
        lines = lines or ["Alpha result Exact Case spaced words", "Beta result", "Beta detail"]
        pages = pages or [1, 2, 2]
        corpus = self.root / f"corpus-{len(list(self.root.iterdir()))}"
        corpus.mkdir()
        (corpus / "originals").mkdir()
        original = b"synthetic original bytes"
        text = "\n".join(lines) + "\n"
        (corpus / "originals" / "REPORT.pdf").write_bytes(original)
        (corpus / "REPORT.txt").write_text(text)
        source = {
            "id": "REPORT",
            "title": "Synthetic report",
            "url": "https://example.org/report.pdf",
            "published": None,
            "dataset_revision": "a" * 40,
            "text_file": "REPORT.txt",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "original_file": "originals/REPORT.pdf",
            "original_sha256": hashlib.sha256(original).hexdigest(),
            "line_locations": [{"page": page} for page in pages],
            "extraction": {"parser": "synthetic"},
        }
        (corpus / "sources.json").write_text(json.dumps({"version": "2", "sources": [source]}))
        binding = {
            "version": "financebench-full-documents-v2",
            "prepared_sha256": canonical_hash(bundle["manifest"]),
            "dataset_revision": "a" * 40,
            "sources_manifest_sha256": hashlib.sha256(
                (corpus / "sources.json").read_bytes()
            ).hexdigest(),
            "source_ids": ["REPORT"],
            "source_hashes": {"REPORT": source["sha256"]},
            "original_hashes": {"REPORT": source["original_sha256"]},
        }
        (corpus / "benchmark_binding.json").write_text(json.dumps(binding))
        return corpus

    @staticmethod
    def evidence(page, text, doc="REPORT"):
        return {"doc_name": doc, "evidence_page_num": page, "evidence_text": text}

    def test_declared_document_scope_uses_permitted_metadata_not_gold(self):
        one = _task("one", "alpha", [self.evidence(0, "Alpha")])
        two = _task("two", "alpha", [self.evidence(0, "Alpha", doc="OTHER")])
        two["metadata"]["doc_name"] = "OTHER"
        bundle = _bundle([one, two])
        corpus = self.corpus(bundle)
        path = corpus / "sources.json"
        manifest = json.loads(path.read_text())
        other = dict(manifest["sources"][0], id="OTHER")
        manifest["sources"].append(other)
        path.write_text(json.dumps(manifest))
        binding_path = corpus / "benchmark_binding.json"
        binding = json.loads(binding_path.read_text())
        binding["source_ids"] = ["OTHER", "REPORT"]
        for field in ["source_hashes", "original_hashes"]:
            binding[field]["OTHER"] = binding[field]["REPORT"]
        binding["sources_manifest_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        binding_path.write_text(json.dumps(binding))
        baseline = evaluate_corpus(bundle, corpus)
        scoped = evaluate_corpus(bundle, corpus, source_scope="declared_document")
        self.assertTrue(
            all(row["searched_source_ids"] == ["OTHER", "REPORT"] for row in baseline["tasks"])
        )
        for row in scoped["tasks"]:
            self.assertEqual(
                row["searched_source_ids"], ["REPORT" if row["id"] == "one" else "OTHER"]
            )
            self.assertTrue(
                all(hit["source_id"] in row["searched_source_ids"] for hit in row["retrieved_hits"])
            )
        self.assertEqual(scoped["source_scope"], "declared_document")

    def test_zero_based_gold_pages_convert_to_one_based_original_pages(self):
        bundle = _bundle([_task("one", "alpha", [self.evidence(0, "Alpha result")])])
        report = evaluate_corpus(bundle, self.corpus(bundle))
        row = report["tasks"][0]
        self.assertEqual(row["expected_distinct_page_keys"], [{"source_id": "REPORT", "page": 1}])
        self.assertEqual(row["evidence_text_concordance"][0]["page"], 1)
        self.assertTrue(row["retrieval"]["top_1"]["all_required_pages_retrieved"])

    def test_multi_page_required_coverage_uses_full_passages(self):
        bundle = _bundle(
            [
                _task(
                    "two-pages",
                    "alpha beta",
                    [self.evidence(0, "Alpha result"), self.evidence(1, "Beta result")],
                )
            ]
        )
        row = evaluate_corpus(bundle, self.corpus(bundle))["tasks"][0]
        self.assertFalse(row["retrieval"]["top_1"]["all_required_pages_retrieved"])
        self.assertTrue(row["retrieval"]["top_3"]["all_required_pages_retrieved"])
        self.assertEqual(row["retrieval"]["top_3"]["expected_page_recall"], 1.0)
        self.assertEqual(
            row["retrieved_hits"][0]["passage_original_locations"],
            [{"page": 2}, {"page": 2}],
        )

    def test_missing_extraction_page_is_reported(self):
        bundle = _bundle([_task("missing", "alpha", [self.evidence(2, "Absent text")])])
        row = evaluate_corpus(bundle, self.corpus(bundle))["tasks"][0]
        self.assertEqual(row["evidence_text_concordance"][0]["status"], "missing_page")
        self.assertFalse(row["evidence_text_concordance"][0]["exact_text_found"])

    def test_gold_is_never_added_to_search_query(self):
        gold = "SECRET GOLD PHRASE"
        bundle = _bundle([_task("query", "alpha only", [self.evidence(0, gold)])])
        corpus = self.corpus(bundle)
        queries = []
        original = Sources.search

        def capture(instance, query, timeout):
            queries.append(query)
            return original(instance, query, timeout)

        with patch.object(Sources, "search", capture):
            evaluate_corpus(bundle, corpus)
        self.assertEqual(queries, ["alpha only"])
        self.assertNotIn(gold, queries[0])

    def test_identity_failures_happen_before_search(self):
        base = _bundle([_task("identity", "alpha", [self.evidence(0, "Alpha")])])
        cases = []

        corpus = self.corpus(base)
        binding_path = corpus / "benchmark_binding.json"
        binding = json.loads(binding_path.read_text())
        binding["prepared_sha256"] = "0" * 64
        binding_path.write_text(json.dumps(binding))
        cases.append((base, corpus, "prepared hash"))

        corpus = self.corpus(base)
        manifest_path = corpus / "sources.json"
        manifest = json.loads(manifest_path.read_text())
        extra_text = "unrelated\n"
        (corpus / "EXTRA.txt").write_text(extra_text)
        manifest["sources"].append(
            {
                "id": "EXTRA",
                "title": "Extra",
                "text_file": "EXTRA.txt",
                "sha256": hashlib.sha256(extra_text.encode()).hexdigest(),
                "line_locations": [{"page": 1}],
            }
        )
        manifest_path.write_text(json.dumps(manifest))
        cases.append((base, corpus, "source IDs"))

        corpus = self.corpus(base)
        (corpus / "REPORT.txt").write_text("tampered\n")
        cases.append((base, corpus, "hash mismatch"))

        corpus = self.corpus(base)
        manifest_path = corpus / "sources.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["sources"] = []
        manifest_path.write_text(json.dumps(manifest))
        cases.append((base, corpus, "no searchable documents"))

        for bundle, candidate, message in cases:
            with (
                self.subTest(message=message),
                patch.object(Sources, "search", side_effect=AssertionError("search must not run")),
                self.assertRaisesRegex(ValueError, message),
            ):
                evaluate_corpus(bundle, candidate)

    def test_original_page_metadata_tampering_fails_before_search(self):
        bundle = _bundle([_task("location", "alpha", [self.evidence(0, "Alpha")])])
        corpus = self.corpus(bundle)
        path = corpus / "sources.json"
        manifest = json.loads(path.read_text())
        manifest["sources"][0]["line_locations"][0]["page"] = 99
        path.write_text(json.dumps(manifest))
        with (
            patch.object(Sources, "search") as search,
            self.assertRaisesRegex(ValueError, "manifest hash"),
        ):
            evaluate_corpus(bundle, corpus)
        search.assert_not_called()

    def test_duplicate_and_missing_original_hashes_fail_before_search(self):
        bundle = _bundle([_task("binding", "alpha", [self.evidence(0, "Alpha")])])
        for mutation, message in (("duplicate", "unique"), ("missing", "original")):
            corpus = self.corpus(bundle)
            if mutation == "duplicate":
                path = corpus / "benchmark_binding.json"
                binding = json.loads(path.read_text())
                binding["source_ids"] = ["REPORT", "REPORT"]
                path.write_text(json.dumps(binding))
            else:
                path = corpus / "sources.json"
                manifest = json.loads(path.read_text())
                manifest["sources"][0].pop("original_file")
                manifest["sources"][0].pop("original_sha256")
                path.write_text(json.dumps(manifest))
            with (
                self.subTest(mutation=mutation),
                patch.object(Sources, "search", side_effect=AssertionError("search must not run")),
                self.assertRaisesRegex(ValueError, message),
            ):
                evaluate_corpus(bundle, corpus)

    def test_concordance_is_case_sensitive_and_whitespace_normalized(self):
        bundle = _bundle(
            [
                _task(
                    "text",
                    "alpha",
                    [
                        self.evidence(0, "Exact   Case\nspaced words"),
                        self.evidence(0, "exact Case spaced words"),
                    ],
                )
            ]
        )
        concordance = evaluate_corpus(bundle, self.corpus(bundle))["tasks"][0][
            "evidence_text_concordance"
        ]
        self.assertEqual([item["status"] for item in concordance], ["found", "not_found"])
        self.assertNotIn("evidence_text", concordance[0])

    def test_all_selected_tasks_remain_in_summary_denominator(self):
        tasks = [
            _task("resolved", "alpha", [self.evidence(0, "Alpha")]),
            _task(
                "unresolved",
                "missingterm",
                [self.evidence(1, "Beta")],
                requires_review=True,
            ),
        ]
        bundle = _bundle(tasks)
        report = evaluate_corpus(bundle, self.corpus(bundle))
        self.assertEqual(report["task_denominator"], 2)
        self.assertEqual(len(report["tasks"]), 2)
        unresolved = next(row for row in report["tasks"] if row["id"] == "unresolved")
        self.assertTrue(unresolved["reference_flags"]["unresolved"])
        self.assertTrue(unresolved["reference_flags"]["diagnostic_only"])
        self.assertEqual(report["summary"]["top_1"]["all_required_pages_task_rate"], 0.5)

    def test_cli_output_contract_data_is_finite(self):
        bundle = _bundle([_task("finite", "alpha", [self.evidence(0, "Alpha")])])
        report = evaluate_corpus(bundle, self.corpus(bundle))
        json.dumps(report, allow_nan=False)
        self.assertEqual(report["fixed_k"], [1, 3, 5])
        self.assertEqual(report["retrieval_version"], "bm25-v2")
        self.assertIn("binding_sha256", report)


if __name__ == "__main__":
    unittest.main()
