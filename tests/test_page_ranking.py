import copy
import hashlib
import json
import math
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

from provenance.page_ranking import compare_page_ranking
from provenance.sources import Sources


class PageRankingTests(unittest.TestCase):
    def sources(self, pages):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name)
        lines = [line for page in pages for line in page]
        text = "\n".join(lines)
        (path / "text.txt").write_text(text)
        source = {
            "id": "synthetic",
            "title": "Synthetic",
            "text_file": "text.txt",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "line_locations": [{"page": n} for n, page in enumerate(pages, 1) for _ in page],
            "extraction": {"page_count": len(pages)},
        }
        (path / "sources.json").write_text(json.dumps({"sources": [source]}))
        return Sources(path)

    def test_default_responses_match_frozen_pre_refactor_oracle(self):
        fixture = json.loads(
            (Path(__file__).parent / "fixtures/page-ranking-baseline.json").read_text()
        )
        sources = self.sources(fixture["pages"])
        for case in fixture["cases"]:
            with self.subTest(version=case["version"], query=case["query"]):
                sources.retrieval_version = case["version"]
                self.assertEqual(
                    json.dumps(sources.search(case["query"], 1)), json.dumps(case["response"])
                )

    def test_shared_pool_preserves_control_and_payloads_without_reading(self):
        sources = self.sources([["assets " * n] for n in range(1, 33)])
        before = copy.deepcopy(sources.documents)
        result = compare_page_ranking(sources, "assets")
        self.assertEqual(result["control"], sources.search("assets", 1)["results"])
        self.assertEqual(len(result["candidates"]), 25)
        self.assertEqual(len(result["page_ranks"]), 32)
        self.assertEqual(len(result["challenger"]), 5)
        self.assertEqual(sources.seen, {})
        self.assertEqual(sources.documents, before)
        for hit in result["challenger"]:
            self.assertIn(hit["start_line"], [r["start_line"] for r in result["candidates"]])
            self.assertEqual(
                hit["snippet"], before["synthetic"]["text"].splitlines()[hit["start_line"] - 1]
            )

    def test_fusion_matches_exact_formula_and_uses_all_pages(self):
        sources = self.sources(
            [
                ["assets assets"] + ["noise " * 50] * 63,
                ["assets"],
                ["unrelated"],
            ]
        )
        result = compare_page_ranking(sources, "assets")
        self.assertEqual(len(result["page_ranks"]), 3)
        self.assertEqual(result["page_ranks"][-1]["score"], 0)
        expected = []
        for candidate in result["candidates"]:
            fused = Fraction(1, 60 + candidate["passage_rank"]) + Fraction(
                1, 60 + candidate["page_rank"]
            )
            self.assertEqual(
                fused, Fraction(candidate["rrf_numerator"], candidate["rrf_denominator"])
            )
            expected.append((fused, candidate["passage_rank"], candidate["start_line"]))
        expected.sort(key=lambda row: (-row[0], row[1]))
        self.assertEqual(
            [h["start_line"] for h in result["challenger"]], [r[2] for r in expected[:5]]
        )
        self.assertEqual(result, compare_page_ranking(sources, "assets"))

    def test_ties_and_empty_query(self):
        sources = self.sources([["assets"], ["assets"], ["other"]])
        result = compare_page_ranking(sources, "assets")
        self.assertEqual([p["page"] for p in result["page_ranks"]], [1, 2, 3])
        self.assertEqual([h["start_line"] for h in result["challenger"]], [1, 2])
        empty = compare_page_ranking(sources, "the what")
        self.assertEqual(empty["candidates"], [])
        self.assertEqual(empty["control"], [])
        self.assertEqual(empty["challenger"], [])

    def test_page_statistics_count_overlapping_source_lines_once(self):
        sources = self.sources([["assets"] * 40, ["other"]])
        result = compare_page_ranking(sources, "assets")
        # Each page adds exactly one title token; page lengths are 41 and 2.
        expected = math.log(2) * 40 * 2.5 / (40 + 1.5 * (0.25 + 0.75 * 41 / 21.5))
        self.assertAlmostEqual(result["page_ranks"][0]["score"], expected)
        self.assertIsNone(result["page_ranks"][1]["rank"])

    def test_raw_page_scores_exact_fusion_tie_and_out_of_pool_page(self):
        sources = self.sources([["assets"], ["assets"]])
        with patch("provenance.page_ranking._bm25", side_effect=[1.00001, 1.00002]):
            result = compare_page_ranking(sources, "assets")
        self.assertEqual([p["page"] for p in result["page_ranks"]], [2, 1])
        # Swapped ranks tie exactly; preserve passage order despite the page order.
        self.assertEqual([h["start_line"] for h in result["challenger"]], [1, 2])
        sources = self.sources([["assets"] for _ in range(26)])
        with patch("provenance.page_ranking._bm25", side_effect=[1] * 25 + [2]):
            result = compare_page_ranking(sources, "assets")
        self.assertEqual(result["page_ranks"][0]["page"], 26)
        self.assertNotIn(26, [c["page"] for c in result["candidates"]])
        self.assertEqual(result["candidates"][0]["page_rank"], 2)

    def test_invalid_mapping_and_cross_page_candidates_fail_explicitly(self):
        for locations in ([], [{"page": True}], [{"page": 2}, {"page": 1}], [{"page": 1}] * 2):
            with self.subTest(locations=locations):
                sources = self.sources([["assets"], ["assets"]])
                sources.documents["synthetic"]["line_locations"] = locations
                with self.assertRaises(ValueError):
                    compare_page_ranking(sources, "assets")
        sources = self.sources([["assets"], ["assets"]])
        sources.passages[0]["end_line"] = 2
        with self.assertRaisesRegex(ValueError, "single-page"):
            compare_page_ranking(sources, "assets")
        for field, value in (("exa_key", "offline-test"), ("retrieval_version", "passage-v1")):
            sources = self.sources([["assets"]])
            setattr(sources, field, value)
            with self.assertRaisesRegex(ValueError, "local bm25-v2"):
                compare_page_ranking(sources, "assets")
