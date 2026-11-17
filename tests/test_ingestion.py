import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from provenance.ingestion import DocumentHTML, ingest
from provenance.sources import Sources, locator_range


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def corpus(self, html=None):
        original = self.root / "original.html"
        original.write_text(html or "<h1>Results</h1><p>Revenue was 120 million.</p>")
        output = self.root / "corpus"
        ingest(
            {
                "sources": [
                    {
                        "id": "test",
                        "title": "Test",
                        "input_file": str(original),
                        "url": "https://example.com/results",
                        "published": "2024-01-01",
                    }
                ]
            },
            output,
        )
        return output

    def test_html_keeps_cell_order_headers_and_excludes_hidden_xbrl(self):
        parser = DocumentHTML()
        parser.feed(
            "<head><title>Ignore</title></head><ix:header>hidden facts</ix:header>"
            "<h1>Income (USD millions)</h1><table><tr><th>Metric</th><th>2024</th></tr>"
            "<tr><td>Revenue</td><td>120</td></tr></table><p>Footnote: unaudited.</p>"
        )
        parser.flush()
        self.assertEqual(
            parser.lines,
            ["Income (USD millions)", "Metric | 2024", "Revenue | 120", "Footnote: unaudited."],
        )
        self.assertTrue(all(loc["section"] == "Income (USD millions)" for loc in parser.locations))

    def test_original_and_extracted_hashes_both_verified(self):
        output = self.corpus()
        sources = Sources(output)
        doc = sources.documents["test"]
        self.assertEqual(
            doc["original_sha256"],
            hashlib.sha256((output / doc["original_file"]).read_bytes()).hexdigest(),
        )
        (output / doc["original_file"]).write_text("tampered original")
        with self.assertRaisesRegex(ValueError, "Original hash mismatch"):
            Sources(output)

    def test_extracted_text_tampering_rejected(self):
        output = self.corpus()
        (output / "test.txt").write_text("tampered extraction")
        with self.assertRaisesRegex(ValueError, "Corpus hash mismatch"):
            Sources(output)

    def test_search_read_preserves_section_and_continuation(self):
        output = self.corpus(
            "<h1>Results</h1>" + "".join(f"<p>Revenue metric {i}</p>" for i in range(90))
        )
        sources = Sources(output)
        hit = sources.search("revenue metric", 1)["results"][0]
        self.assertLessEqual(hit["end_line"] - hit["start_line"] + 1, 32)
        read = sources.read("test", hit["start_line"], hit["end_line"], 1)
        self.assertEqual(read["lines"][0]["original_location"], {"section": "Results"})
        self.assertEqual(read["next_start_line"], read["lines"][-1]["line"] + 1)
        self.assertFalse(read["context_complete"])
        sources.check_citation(
            {"source_id": "test", "locator": read["locator"], "quote": read["lines"][0]["text"]}
        )

    def test_passages_cover_every_line_across_section_boundaries(self):
        output = self.corpus(
            "".join(f"<h1>Section {n}</h1>" + "<p>metric evidence</p>" * 37 for n in range(4))
        )
        sources = Sources(output)
        covered = set()
        for passage in sources.passages:
            covered.update(range(passage["start_line"], passage["end_line"] + 1))
        self.assertEqual(
            covered, set(range(1, len(sources.documents["test"]["text"].splitlines()) + 1))
        )

    def test_scope_filter_does_not_retrieve_excluded_passages(self):
        sources = Sources(self.corpus())
        sources.documents = {}
        self.assertEqual(sources.search("revenue", 1)["results"], [])

    def test_corpus_version_cannot_be_silently_overwritten(self):
        output = self.corpus()
        with self.assertRaisesRegex(ValueError, "already exists"):
            ingest({"sources": []}, output)

    def test_location_count_tampering_rejected(self):
        output = self.corpus()
        manifest_path = output / "sources.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["sources"][0]["line_locations"].pop()
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "location count"):
            Sources(output)

    def test_legacy_retrieval_preserves_prefix_schema_and_score(self):
        sources = Sources(self.corpus(), retrieval_version="passage-v1")
        hit = sources.search("revenue", 1)["results"][0]
        self.assertEqual(hit["score"], 0.4055)
        self.assertEqual(hit["snippet"], sources.passages[0]["text"][:1000])
        self.assertNotIn("snippet_locator", hit)
        self.assertEqual(sources.retrieval_version, "passage-v1")
        with self.assertRaisesRegex(ValueError, "retrieval_version"):
            Sources(self.root / "corpus", retrieval_version="unknown")

    def test_bm25_length_normalization_favors_concise_distinctive_evidence(self):
        long = self.root / "long.txt"
        short = self.root / "short.txt"
        long.write_text("common " * 1000 + "distinctive\n")
        short.write_text("common distinctive\n")
        output = self.root / "ranking"
        ingest(
            {
                "sources": [
                    {"id": path.stem, "title": "Evidence", "input_file": str(path)}
                    for path in (long, short)
                ]
            },
            output,
        )
        hits = Sources(output).search("common distinctive", 1)["results"]
        self.assertEqual(hits[0]["id"], "short")
        self.assertGreater(hits[0]["score"], hits[1]["score"])

    def test_query_focused_snippet_reveals_late_exact_lines(self):
        lines = ["Unrelated preceding narrative " + "padding " * 20 for _ in range(15)]
        lines += ["Distinctive retention measure was 111 percent.", "Footnote: illustrative."]
        output = self.corpus("<h1>Results</h1>" + "".join(f"<p>{line}</p>" for line in lines))
        sources = Sources(output)
        hit = sources.search("distinctive retention", 1)["results"][0]
        self.assertIn("Distinctive retention measure was 111 percent.", hit["snippet"])
        self.assertLessEqual(len(hit["snippet"]), 1000)
        start, end = locator_range(hit["snippet_locator"])
        self.assertGreater(start, 10)
        actual = sources.documents["test"]["text"].splitlines()[start - 1 : end]
        self.assertEqual(hit["snippet"], "\n".join(actual))
        self.assertLessEqual(hit["start_line"], start)
        self.assertGreaterEqual(hit["end_line"], end)

    def test_full_packet_pdf_pages_are_mapped_and_searchable(self):
        corpus = Path(__file__).resolve().parents[1] / "data" / "cloudflare-2024-q3"
        sources = Sources(corpus)
        deck = sources.documents["cloudflare-investor-day-2024"]
        self.assertEqual({loc["page"] for loc in deck["line_locations"]}, set(range(1, 117)))
        self.assertEqual(deck["extraction"]["text_completeness"], "not_verified")
        self.assertTrue(sources.search("Cloudflare Investor Day", 1)["results"])
