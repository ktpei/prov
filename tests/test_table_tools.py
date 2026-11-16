import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from provenance.ingestion import ingest
from provenance.table_structure import extract_html_tables
from provenance.table_tools import MAX_RESPONSE_CHARACTERS, TableSources


class TableSourcesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.html = self.root / "fixture.html"
        self.html.write_text(
            """<html><body><table id="facts"><caption>Quarterly raw facts</caption>
<tr><th id="metric" scope="col">Metric</th><th id="value" scope="col">Value</th></tr>
<tr><td>Header context one</td><td>1</td></tr>
<tr><td>Header context two</td><td>2</td></tr>
<tr><td>Header context three</td><td>3</td></tr>
<tr><td>Header context four</td><td>4</td></tr>
<tr><td>Prior expense label</td><td></td></tr>
<tr><td headers="metric">Expense</td><td>(</td><td>1,234</td><td>)</td></tr>
<tr><td>Prior revenue label</td><td>USD</td></tr>
<tr><td>Needle revenue</td><td>42</td><td hidden>999999</td></tr>
<tr><td>Unrelated middle row</td><td>7</td></tr>
<tr><td>Prior late label</td><td>units</td></tr>
<tr><td>Late distinctive beta</td><td>0</td></tr>
</table></body></html>""",
            encoding="utf-8",
        )
        notes = self.root / "notes.txt"
        notes.write_text("plain non-HTML source\n", encoding="utf-8")
        self.corpus = self.root / "corpus"
        ingest(
            {
                "sources": [
                    {"id": "html-source", "title": "Fixture", "input_file": str(self.html)},
                    {"id": "text-source", "title": "Notes", "input_file": str(notes)},
                ]
            },
            self.corpus,
        )
        self.tables = TableSources(self.corpus)

    def call(self, name, args, timeout=1):
        return self.tables.call(name, args, timeout)

    def read(self, rows):
        return self.call(
            "read_table",
            {"source_id": "html-source", "table_id": "table-1", "row_indices": rows},
        )

    def test_constructor_rejects_original_hash_tampering(self):
        manifest = json.loads((self.corpus / "sources.json").read_text())
        source = next(item for item in manifest["sources"] if item["id"] == "html-source")
        (self.corpus / source["original_file"]).write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Original hash mismatch"):
            TableSources(self.corpus)

    def test_identity_and_manifest_hash_are_exact(self):
        result = self.read([8])
        manifest = json.loads((self.corpus / "sources.json").read_text())
        source = next(item for item in manifest["sources"] if item["id"] == "html-source")
        self.assertEqual(result["source_id"], "html-source")
        self.assertEqual(result["original_sha256"], source["original_sha256"])
        self.assertEqual(result["sidecar_version"], "native-html-tables-v2")
        self.assertEqual(
            result["corpus_manifest_sha256"],
            hashlib.sha256((self.corpus / "sources.json").read_bytes()).hexdigest(),
        )

    def test_search_is_source_scoped_lexical_and_returns_matched_rows(self):
        result = self.call("search_tables", {"source_id": "html-source", "query": "needle"})
        self.assertEqual(len(result["results"]), 1)
        hit = result["results"][0]
        self.assertEqual(hit["source_id"], "html-source")
        self.assertEqual(hit["table_id"], "table-1")
        self.assertEqual(hit["matched_row_indices"], [8])
        self.assertIn("Needle revenue", hit["literal_match_snippets"][0]["text"])
        self.assertFalse(result["diagnostics"]["semantic_matching"])
        self.assertNotIn("gold", json.dumps(result).lower())

    def test_hidden_numeric_cell_is_excluded_from_search_and_read(self):
        search = self.call("search_tables", {"source_id": "html-source", "query": "999999"})
        self.assertEqual(search["results"], [])
        read = self.read([8])
        self.assertNotIn("999999", [cell["text"] for cell in read["cells"]])
        self.assertTrue(read["diagnostics"]["explicitly_hidden_cells_omitted"])

    def test_read_returns_exact_v2_cell_records_and_raw_caption(self):
        manifest = json.loads((self.corpus / "sources.json").read_text())
        source = next(item for item in manifest["sources"] if item["id"] == "html-source")
        sidecar = extract_html_tables(self.corpus / source["original_file"])
        table = sidecar["tables"][0]
        result = self.read([8])
        expected = [
            cell
            for index in result["included_row_indices"]
            for cell in table["rows"][index]["cells"]
            if cell["text"] and cell["visibility"] != "explicitly_hidden"
        ]
        self.assertEqual(result["cells"], expected)
        self.assertEqual(result["caption"], table["caption"])
        self.assertEqual(result["read_policy"], "table-window-v1")

    def test_first_five_and_preceding_rows_are_deduplicated_and_sorted(self):
        result = self.read([8, 11])
        self.assertEqual(result["requested_row_indices"], [8, 11])
        self.assertEqual(result["included_row_indices"], [0, 1, 2, 3, 4, 7, 8, 10, 11])

    def test_split_parentheses_geometry_and_zero_are_preserved(self):
        result = self.read([6, 11])
        row_six = [cell for cell in result["cells"] if cell["row_start"] == 6]
        self.assertEqual([cell["text"] for cell in row_six], ["Expense", "(", "1,234", ")"])
        self.assertEqual([cell["column_start"] for cell in row_six], [0, 1, 2, 3])
        self.assertIn("0", [cell["text"] for cell in result["cells"]])
        self.assertNotIn("", [cell["text"] for cell in result["cells"]])

    def test_row_index_validation_rejects_bool_duplicates_negative_and_bounds(self):
        cases = ([True], [8, 8], [-1], [12], list(range(9)))
        for rows in cases:
            with self.subTest(rows=rows):
                result = self.read(rows)
                self.assertEqual(set(result), {"error"})

    def test_unknown_non_html_bad_fields_query_and_timeout_are_tool_errors(self):
        calls = [
            ("read_table", {"source_id": "missing", "table_id": "table-1", "row_indices": []}, 1),
            (
                "read_table",
                {"source_id": "text-source", "table_id": "table-1", "row_indices": []},
                1,
            ),
            (
                "read_table",
                {"source_id": "html-source", "table_id": "missing", "row_indices": []},
                1,
            ),
            ("search_tables", {"source_id": "html-source", "query": ""}, 1),
            ("search_tables", {"source_id": "html-source", "query": "x" * 501}, 1),
            ("search_tables", {"source_id": "html-source", "query": 7}, 1),
            ("unknown", {}, 1),
            ("read_table", [], 1),
            (
                "read_table",
                {"source_id": "html-source", "table_id": "table-1", "row_indices": []},
                True,
            ),
            (
                "read_table",
                {"source_id": "html-source", "table_id": "table-1", "row_indices": []},
                0,
            ),
            (
                "read_table",
                {"source_id": "html-source", "table_id": "table-1", "row_indices": []},
                float("nan"),
            ),
        ]
        for name, args, timeout in calls:
            with self.subTest(name=name, args=args, timeout=timeout):
                result = self.call(name, args, timeout)
                self.assertEqual(set(result), {"error"})
                self.assertTrue(result["error"])

    def test_search_candidates_exclude_rows_already_in_read_prefix(self):
        result = self.call(
            "search_tables", {"source_id": "html-source", "query": "header context needle revenue"}
        )
        hit = result["results"][0]
        self.assertIn(8, hit["matched_row_indices"])
        self.assertTrue(all(index >= 5 for index in hit["matched_row_indices"]))
        prefix_only = self.call(
            "search_tables", {"source_id": "html-source", "query": "header context"}
        )
        self.assertEqual(prefix_only["results"][0]["matched_row_indices"], [])
        self.assertTrue(prefix_only["results"][0]["literal_match_snippets"])

    def test_legacy_search_version_preserves_prefix_candidates_and_table_scores(self):
        args = {"source_id": "html-source", "query": "header context needle revenue"}
        old = TableSources(self.corpus, search_version="source-scoped-visible-row-bm25-v1").call(
            "search_tables", args, 1
        )
        new = self.call("search_tables", args)
        self.assertTrue(any(index < 5 for index in old["results"][0]["matched_row_indices"]))
        self.assertEqual(
            [(h["table_id"], h["score"]) for h in old["results"]],
            [(h["table_id"], h["score"]) for h in new["results"]],
        )
        self.assertNotIn("read_candidate_policy", old["diagnostics"])
        with self.assertRaisesRegex(ValueError, "version"):
            TableSources(self.corpus, search_version="unknown")

    def test_soft_prefix_candidates_preserve_metric_evidence_and_table_scores(self):
        challenger = TableSources(self.corpus, search_version="source-scoped-visible-row-bm25-v3")
        for query in ("quarterly", "header context needle revenue", "expense", "999999"):
            with self.subTest(query=query):
                old = self.tables.search_tables("html-source", query)
                new = challenger.search_tables("html-source", query)
                self.assertEqual(
                    [(h["table_id"], h["score"]) for h in old["results"]],
                    [(h["table_id"], h["score"]) for h in new["results"]],
                )
                self.assertEqual(new, challenger.search_tables("html-source", query))
        self.assertEqual(
            challenger.search_tables("html-source", "quarterly")["results"][0][
                "matched_row_indices"
            ],
            [],
        )
        # A metric repeated in the prefix must retain positive body evidence.
        html = self.root / "repeated.html"
        html.write_text(
            "<table><caption>Net margin</caption>"
            + "<tr><td>Reporting period 2040</td></tr>" * 5
            + "<tr><td>Net margin</td><td>17</td></tr>"
            + "<tr><td>Reporting period 2040</td><td>29</td></tr></table>"
        )
        corpus = self.root / "repeated-corpus"
        ingest(
            {"sources": [{"id": "synthetic", "title": "Invented facts", "input_file": str(html)}]},
            corpus,
        )
        tool = TableSources(corpus, search_version="source-scoped-visible-row-bm25-v3")
        self.assertEqual(
            tool.search_tables("synthetic", "net margin")["results"][0]["matched_row_indices"], [5]
        )
        self.assertEqual(
            tool.search_tables("synthetic", "2040")["results"][0]["matched_row_indices"], [6]
        )
        self.assertEqual(
            tool.read_table("synthetic", "table-1", [5]),
            TableSources(corpus).read_table("synthetic", "table-1", [5]),
        )

    def test_soft_prefix_reranks_before_limit_and_keeps_body_only_order(self):
        html = self.root / "candidate-limit.html"
        prefix = " ".join(f"calendar{i}" for i in range(40))
        html.write_text(
            "<table><caption>Repeated calendar</caption>"
            + f"<tr><td>{prefix}</td></tr>" * 5
            + f"<tr><td>{prefix}</td></tr>" * 9
            + "<tr><td>invented metric "
            + "detail " * 80
            + "</td></tr></table>"
        )
        corpus = self.root / "candidate-limit-corpus"
        ingest(
            {"sources": [{"id": "synthetic", "title": "Invented facts", "input_file": str(html)}]},
            corpus,
        )
        old = TableSources(corpus)
        new = TableSources(corpus, search_version="source-scoped-visible-row-bm25-v3")
        query = prefix + " invented metric"
        before = old.search_tables("synthetic", query)["results"][0]
        after = new.search_tables("synthetic", query)["results"][0]
        self.assertEqual(before["score"], after["score"])
        self.assertNotIn(14, before["matched_row_indices"])
        self.assertEqual(after["matched_row_indices"][0], 14)
        for query in ("invented metric", "calendar"):
            self.assertEqual(
                old.search_tables("synthetic", query)["results"],
                new.search_tables("synthetic", query)["results"],
            )

    def test_returned_cells_and_captions_cannot_mutate_snapshot(self):
        original = self.read([8])
        changed = self.read([8])
        changed["cells"][0]["text"] = "forged"
        changed["cells"][0]["original_location"]["line"] = 999
        changed["caption"]["text"] = "forged units"
        self.assertEqual(self.read([8]), original)
        self.assertEqual(len(original["sidecar_sha256"]), 64)

    def test_repeated_calls_are_deterministic_and_do_not_write_corpus(self):
        def hashes():
            return {
                path.relative_to(self.corpus): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.corpus.rglob("*")
                if path.is_file()
            }

        before = hashes()
        first = self.read([8, 11])
        second = self.read([8, 11])
        search_first = self.call(
            "search_tables", {"source_id": "html-source", "query": "distinctive beta"}
        )
        search_second = self.call(
            "search_tables", {"source_id": "html-source", "query": "distinctive beta"}
        )
        self.assertEqual(first, second)
        self.assertEqual(search_first, search_second)
        self.assertEqual(hashes(), before)

    def test_oversize_read_fails_atomically_without_truncation(self):
        huge = self.root / "huge.html"
        huge.write_text(
            "<table><tr><td>" + ("x" * MAX_RESPONSE_CHARACTERS) + "</td></tr></table>",
            encoding="utf-8",
        )
        corpus = self.root / "huge-corpus"
        ingest({"sources": [{"id": "huge", "input_file": str(huge)}]}, corpus)
        result = TableSources(corpus).call(
            "read_table",
            {"source_id": "huge", "table_id": "table-1", "row_indices": [0]},
            1,
        )
        self.assertEqual(set(result), {"error"})
        self.assertIn("exceeds", result["error"])
        self.assertLessEqual(
            len(json.dumps(result, separators=(",", ":"))), MAX_RESPONSE_CHARACTERS
        )


if __name__ == "__main__":
    unittest.main()
