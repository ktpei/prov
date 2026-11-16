import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from provenance.table_structure import MAX_SPAN, extract_html_tables


def extract(tmp_path, html):
    path = tmp_path / "input.html"
    path.write_text(html, encoding="utf-8")
    return extract_html_tables(path)


class TableStructureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp_path = Path(temporary.name)

    def test_v3_excludes_inert_tables_without_changing_visible_ids(self):
        path = self.tmp_path / "input.html"
        path.write_text(
            "<template><table><tr><td>999</td></tr></table></template>"
            "<table><tr><td>42</td></tr></table>"
        )
        legacy = extract_html_tables(path)
        self.assertEqual(len(legacy["tables"]), 2)
        result = extract_html_tables(path, version="native-html-tables-v3")
        self.assertEqual(result["version"], "native-html-tables-v3")
        self.assertEqual(len(result["tables"]), 1)
        self.assertEqual(result["tables"][0]["id"], "table-1")
        self.assertEqual(result["tables"][0]["rows"][0]["cells"][0]["text"], "42")
        self.assertEqual(extract_html_tables(path, version="native-html-tables-v2"), legacy)

    def test_v3_template_fragment_cannot_change_parent_geometry_or_text(self):
        path = self.tmp_path / "input.html"
        path.write_text(
            "<table><caption>USD<template>millions</template> thousands</caption>"
            "<tr><td>4<template><tr><td rowspan=500>999"
            "<template><table><tr><td>888</table></template></template>2</td>"
            "<td>0</td></tr><template><tr><td>777</template>"
            "<tr><td>7</td></tr></table>"
        )
        result = extract_html_tables(path, version="native-html-tables-v3")
        table = result["tables"][0]
        self.assertEqual(len(result["tables"]), 1)
        self.assertEqual(table["caption"]["text"], "USD thousands")
        self.assertEqual(
            [[c["text"] for c in r["cells"]] for r in table["rows"]], [["42", "0"], ["7"]]
        )
        self.assertEqual(table["rows"][1]["cells"][0]["column_start"], 0)

    def test_v3_template_inside_hidden_cell_does_not_end_hidden_scope(self):
        path = self.tmp_path / "input.html"
        path.write_text("<table><tr><td hidden><template><td>999</template>888<td>42</table>")
        result = extract_html_tables(path, version="native-html-tables-v3")
        self.assertEqual([c["text"] for c in result["tables"][0]["rows"][0]["cells"]], ["", "42"])

    def test_v3_rejects_ambiguous_templates_and_unknown_versions(self):
        path = self.tmp_path / "input.html"
        for html in [
            "<template/>",
            "<template>",
            "</template>",
            "<template shadowrootmode=open></template>",
            "<template><template/></template>",
        ]:
            path.write_text(html)
            with self.subTest(html=html), self.assertRaises(ValueError):
                extract_html_tables(path, version="native-html-tables-v3")
        with self.assertRaisesRegex(ValueError, "Unknown table extraction version"):
            extract_html_tables(path, version="unrecognized")

    def test_v3_cli_selects_template_suppression(self):
        path = self.tmp_path / "input.html"
        path.write_text("<template><table><tr><td>999</td></tr></table></template>")
        output = self.tmp_path / "v3.json"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "provenance.table_structure",
                str(path),
                str(output),
                "--version",
                "native-html-tables-v3",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(output.read_text())["tables"], [])

    def test_v3_raw_text_cannot_escape_template_suppression(self):
        path = self.tmp_path / "input.html"
        for tag in [
            "textarea",
            "title",
            "xmp",
            "iframe",
            "noembed",
            "noframes",
            "noscript",
            "plaintext",
        ]:
            path.write_text(
                f"<table><tr><td>42<template><{tag}></template>999<template>"
                f"</{tag}></template></td></tr></table>"
            )
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "raw-text context"):
                extract_html_tables(path, version="native-html-tables-v3")
        for tag in ["script", "style"]:
            path.write_text(
                f"<table><tr><td>42<template><{tag}></template>999<template>"
                f"</{tag}></template></td></tr></table>"
            )
            result = extract_html_tables(path, version="native-html-tables-v3")
            self.assertEqual(result["tables"][0]["rows"][0]["cells"][0]["text"], "42")

    def test_v3_literal_template_tags_in_visible_raw_text_are_rejected(self):
        path = self.tmp_path / "input.html"
        for tag in [
            "textarea",
            "title",
            "xmp",
            "iframe",
            "noembed",
            "noframes",
            "noscript",
            "plaintext",
        ]:
            path.write_text(
                f"<table><tr><td><{tag}>4<template>999</template>2</{tag}></td></tr></table>"
            )
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "raw-text context"):
                extract_html_tables(path, version="native-html-tables-v3")
        path.write_text("<head><title>Example</title></head><table><tr><td>42</td></tr></table>")
        result = extract_html_tables(path, version="native-html-tables-v3")
        self.assertEqual(result["tables"][0]["rows"][0]["cells"][0]["text"], "42")

    def test_block_boundaries_and_caption_break_do_not_merge_values(self):
        result = extract(
            self.tmp_path,
            "<table><caption>USD<br>thousands</caption><tr><td><div>42</div><div>99</div></td></tr></table>",
        )
        self.assertEqual(result["tables"][0]["caption"]["text"], "USD thousands")
        self.assertEqual(result["tables"][0]["rows"][0]["cells"][0]["text"], "42 99")
        result = extract(
            self.tmp_path,
            "<table><tr><td><section>42</section><section>99</section></td></tr></table>",
        )
        self.assertEqual(result["tables"][0]["rows"][0]["cells"][0]["text"], "42 99")

    def test_nested_table_boundaries_do_not_merge_parent_numbers(self):
        result = extract(
            self.tmp_path,
            "<table><tr><td>42<table><tr><td>child</td></tr></table>99</td></tr></table>",
        )
        self.assertEqual(result["tables"][0]["rows"][0]["cells"][0]["text"], "42 99")

    def test_hidden_nonvoid_self_closing_rejected_and_important_whitespace_supported(self):
        for html in [
            "<table><tr hidden/><td>999</td></tr></table>",
            "<div hidden/><table><tr><td>999</td></tr></table></div>",
            "<table><tr><td hidden/><table/><tr><td>999</td></tr></table><td>42</td></tr></table>",
        ]:
            with (
                self.subTest(html=html),
                self.assertRaisesRegex(ValueError, "self-closing non-void"),
            ):
                extract(self.tmp_path, html)
        result = extract(
            self.tmp_path,
            "<table><tr><td>42<span style='display:none ! important'>999</span></td></tr></table>",
        )
        self.assertEqual(result["tables"][0]["rows"][0]["cells"][0]["text"], "42")

    def test_hidden_self_closing_cells_stay_hidden_until_next_cell(self):
        for middle in ["99", "<table><tr><td>999</td></tr></table>"]:
            result = extract(
                self.tmp_path, f"<table><tr><td hidden/>{middle}<td>42</td></tr></table>"
            )
            self.assertEqual(len(result["tables"]), 1)
            self.assertEqual(
                [c["text"] for c in result["tables"][0]["rows"][0]["cells"]], ["", "42"]
            )

    def test_headers_data_text_locations_and_stability(self):
        html = '<table id="facts">\n<tr><th>Name<br>label</th><th>Value</th></tr>\n<tr><td>A &amp; B</td><td>3</td></tr></table>'
        first = extract(self.tmp_path, html)
        second = extract(self.tmp_path, html)

        assert first == second
        assert first["version"] == "native-html-tables-v2"
        assert first["original_sha256"] == hashlib.sha256(html.encode()).hexdigest()
        table = first["tables"][0]
        assert table["id"] == "table-1"
        assert table["html_id"] == "facts"
        assert table["original_location"] == {"line": 1, "column": 0}
        assert [(cell["tag"], cell["text"]) for cell in table["rows"][0]["cells"]] == [
            ("th", "Name label"),
            ("th", "Value"),
        ]
        cell = table["rows"][1]["cells"][0]
        assert cell["id"] == "table-1-r1-c0"
        assert cell["original_location"] == {"line": 3, "column": 4}
        assert cell["text"] == "A & B"

    def test_colspan_and_rowspan_geometry(self):
        result = extract(
            self.tmp_path,
            "<table><tr><td rowspan=2>A</td><td colspan=2>B</td></tr>"
            "<tr><td>C</td><td>D</td></tr></table>",
        )
        rows = result["tables"][0]["rows"]
        assert [(c["column_start"], c["row_span"], c["column_span"]) for c in rows[0]["cells"]] == [
            (0, 2, 1),
            (1, 1, 2),
        ]
        assert [(c["id"], c["column_start"]) for c in rows[1]["cells"]] == [
            ("table-1-r1-c1", 1),
            ("table-1-r1-c2", 2),
        ]

    def test_empty_and_separate_parenthesis_cells_remain(self):
        row = extract(
            self.tmp_path, "<table><tr><td></td><td>(</td><td>1,234</td><td>)</td></tr></table>"
        )["tables"][0]["rows"][0]
        assert [cell["text"] for cell in row["cells"]] == ["", "(", "1,234", ")"]
        assert [cell["column_start"] for cell in row["cells"]] == [0, 1, 2, 3]

    def test_hidden_content_omitted(self):
        result = extract(
            self.tmp_path,
            "<head><table><tr><td>hidden table</td></tr></table></head>"
            "<table><tr><td>A<script>bad</script><style>worse</style>"
            "<noscript>fallback</noscript><ix:header>xbrl</ix:header>B</td></tr></table>",
        )
        assert len(result["tables"]) == 1
        assert result["tables"][0]["rows"][0]["cells"][0]["text"] == "AB"

    def test_explicitly_hidden_content_and_cells(self):
        result = extract(
            self.tmp_path,
            "<table><caption>Visible <span hidden>caption</span></caption>"
            "<tr><td>42<span hidden>99</span><span style=' DISPLAY : none !IMPORTANT '>x</span>"
            "<span style='visibility: Collapse'>y</span> tail<span hidden></span> after<input hidden/> end</td>"
            "<td hidden colspan=2>hidden cell</td><th style='display:none'>hidden header</th></tr>"
            "<tr hidden><td>hidden row cell</td></tr></table>",
        )
        table = result["tables"][0]
        assert table["caption"]["text"] == "Visible"
        assert [cell["text"] for row in table["rows"] for cell in row["cells"]] == [
            "42 tail after end",
            "",
            "",
            "",
        ]
        assert [cell["visibility"] for row in table["rows"] for cell in row["cells"]] == [
            "not_explicitly_hidden",
            "explicitly_hidden",
            "explicitly_hidden",
            "explicitly_hidden",
        ]
        assert [cell["column_start"] for cell in table["rows"][0]["cells"]] == [0, 1, 3]

    def test_hidden_tables_and_nested_wrappers_do_not_leak(self):
        result = extract(
            self.tmp_path,
            "<table><tr><td>parent <div hidden><table><caption>hidden</caption>"
            "<tr><td>child</td></tr></table></div> tail</td></tr></table>"
            "<table style='display: none'><tr><td>removed</td></tr></table>",
        )
        assert len(result["tables"]) == 1
        assert result["tables"][0]["rows"][0]["cells"][0]["text"] == "parent tail"

    def test_html_header_metadata_is_preserved_without_resolution(self):
        table = extract(
            self.tmp_path,
            '<table><caption>  Quarterly   facts </caption><tr><th id="h" scope="col">Name</th>'
            '<td id="v" headers="h group  ">42</td></tr></table>',
        )["tables"][0]
        assert table["caption"] == {
            "text": "Quarterly facts",
            "original_location": {"line": 1, "column": 7},
        }
        assert table["rows"][0]["cells"][0]["scope"] == "col"
        assert table["rows"][0]["cells"][1]["headers"] == ["h", "group"]
        assert table["rows"][0]["cells"][1]["html_id"] == "v"

    def test_nested_tables_are_independent(self):
        result = extract(
            self.tmp_path,
            "<table><tr><td>parent <table><tr><td>child</td></tr></table> tail</td></tr></table>",
        )
        assert [table["id"] for table in result["tables"]] == ["table-1", "table-2"]
        assert result["tables"][0]["rows"][0]["cells"][0]["text"] == "parent tail"
        assert result["tables"][1]["rows"][0]["cells"][0]["text"] == "child"

    def test_invalid_spans_rejected(self):
        for attribute in [
            "rowspan=0",
            "colspan=-1",
            "rowspan=nope",
            f"colspan={MAX_SPAN + 1}",
            "rowspan=1 rowspan=2",
        ]:
            with (
                self.subTest(attribute=attribute),
                self.assertRaisesRegex(ValueError, "Invalid|Duplicate|Unsupported"),
            ):
                extract(self.tmp_path, f"<table><tr><td {attribute}>x</td></tr></table>")

    def test_rowspan_zero_is_explicitly_unsupported(self):
        with self.assertRaisesRegex(ValueError, "Unsupported rowspan=0"):
            extract(self.tmp_path, "<table><tr><td rowspan=0>x</td></tr></table>")

    def test_overlap_and_unfinished_structures_rejected(self):
        with self.assertRaisesRegex(ValueError, "overlaps"):
            extract(
                self.tmp_path,
                "<table><tr><td></td><td rowspan=2></td></tr><tr><td colspan=2></td></tr></table>",
            )
        with self.assertRaisesRegex(ValueError, "Unfinished active cell"):
            extract(self.tmp_path, "<table><tr><td>unfinished")
        with self.assertRaisesRegex(ValueError, "outside an active row"):
            extract(self.tmp_path, "<table><td>missing row</td></table>")

    def test_optional_cell_and_row_end_tags(self):
        result = extract(self.tmp_path, "<table><tr><td>A<td>B<tr><td>C</table>")
        assert [[cell["text"] for cell in row["cells"]] for row in result["tables"][0]["rows"]] == [
            ["A", "B"],
            ["C"],
        ]

    def test_cli_requires_new_file_and_reports_counts_and_hashes(self):
        source = self.tmp_path / "source.html"
        output = self.tmp_path / "sidecar.json"
        source.write_text("<table><tr><td>x</td></tr></table>")
        command = [sys.executable, "-m", "provenance.table_structure", str(source), str(output)]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        report = json.loads(completed.stdout)

        assert (report["tables"], report["rows"], report["cells"]) == (1, 1, 1)
        assert set(report) == {"tables", "rows", "cells", "original_sha256", "sidecar_sha256"}
        assert json.loads(output.read_text())["tables"][0]["id"] == "table-1"
        with self.assertRaises(subprocess.CalledProcessError):
            subprocess.run(command, check=True, capture_output=True, text=True)
