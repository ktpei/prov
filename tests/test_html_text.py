import json
import tempfile
import unittest
from pathlib import Path

from provenance.html_text import DocumentHTMLV2
from provenance.ingestion import extract, ingest


def parse(html):
    parser = DocumentHTMLV2()
    parser.feed(html)
    parser.close()
    return parser


class HTMLTextTests(unittest.TestCase):
    def test_hidden_inline_numbers_and_templates_do_not_contaminate_text(self):
        for element in (
            "<span hidden>999</span>",
            '<span style="display: none ! important">999</span>',
            '<span style="visibility:collapse">999</span>',
            "<template><p>999</p></template>",
            "<ix:header><ix:hidden>999</ix:hidden></ix:header>",
        ):
            with self.subTest(element=element):
                self.assertEqual(parse(f"<p>4{element}2</p>").lines, ["42"])

    def test_hidden_heading_cannot_change_section(self):
        result = parse("<h2>USD millions</h2><h2 hidden>USD billions</h2><p>Revenue 42</p>")
        self.assertEqual(result.lines, ["USD millions", "Revenue 42"])
        self.assertEqual(result.locations, [{"section": "USD millions"}] * 2)

    def test_hidden_cells_rows_nested_tables_and_xml_keep_scope(self):
        examples = [
            "<table><tr><td hidden><table><tr><td>999</td></tr></table><td>42</td></tr></table>",
            "<table><tr hidden><td>999<tr><td>42</table>",
            "<table><tr><td hidden><ix:nonFraction/>999<td>42</td></tr></table>",
            "<table><tr><td hidden/>999<td>42</td></tr></table>",
        ]
        for html in examples:
            with self.subTest(html=html):
                self.assertEqual(parse(html).lines, ["42"])
        self.assertEqual(parse("<table><tr><td>4<td hidden>999<td>2</table>").lines, ["4 | 2"])

    def test_ambiguous_suppression_is_rejected(self):
        examples = [
            "<table><tr><td hidden/><table/><tr><td>999</td></tr></table><td>42</td></tr></table>",
            "<table><tr><td><span hidden>999</table><p>42</p>",
            "<ix:header>999</head><p>888</p></ix:header><p>42</p>",
            "<div hidden><span>999</div><p>42</p>",
            "<span hidden>999",
            "<div hidden/>999",
        ]
        for html in examples:
            with self.subTest(html=html), self.assertRaises(ValueError):
                parse(html)

    def test_implicit_starts_cannot_escape_hidden_wrappers(self):
        for wrapper in ("template", "ix:header", "span hidden"):
            close = wrapper.split()[0]
            for body in ("<td>999</td>", "<tr><td>999</td></tr>"):
                html = f"<table><tr><td>42<{wrapper}>{body}</{close}></td></tr></table>"
                with self.subTest(html=html), self.assertRaises(ValueError):
                    parse(html)

    def test_heading_line_breaks_keep_complete_unit_context(self):
        result = parse("<h2>USD<br>millions</h2><p>Revenue 42</p>")
        self.assertEqual(result.lines, ["USD millions", "Revenue 42"])
        self.assertEqual(result.locations[-1], {"section": "USD millions"})

    def test_visible_blocks_signs_zero_and_inline_xbrl_are_preserved(self):
        result = parse(
            "<table><tr><td><section>42</section><section>99</section></td>"
            "<td>(<ix:nonFraction>0</ix:nonFraction>)</td></tr></table>"
        )
        self.assertEqual(result.lines, ["42 99 | (0)"])
        self.assertEqual(
            parse("<p>Before</p><table><tr><td>42</td></tr></table><p>After</p>").lines,
            ["Before", "42", "After"],
        )

    def test_versions_are_explicit_and_legacy_output_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "facts.html"
            original.write_text("<h2>Facts</h2><p>42<span hidden>999</span></p>")
            legacy = extract(original)
            self.assertEqual(legacy, extract(original, html_text_version="stdlib-html-v1"))
            self.assertEqual(legacy[0], ["Facts", "42999"])
            self.assertEqual(legacy[2]["parser"], "stdlib-html")
            fixed = extract(original, html_text_version="native-html-text-v2")
            self.assertEqual(fixed[0], ["Facts", "42"])
            self.assertEqual(fixed[2]["parser"], "native-html-text-v2")
            self.assertEqual(fixed[2]["text_completeness"], "not_verified")
            output = root / "corpus"
            packet = {"sources": [{"id": "facts", "input_file": str(original)}]}
            ingest(packet, output, html_text_version="native-html-text-v2")
            manifest = json.loads((output / "sources.json").read_text())
            self.assertEqual(manifest["sources"][0]["extraction"], fixed[2])
            self.assertEqual((output / "facts.txt").read_text(), "Facts\n42\n")
            with self.assertRaisesRegex(ValueError, "already exists"):
                ingest(packet, output, html_text_version="native-html-text-v2")
            with self.assertRaisesRegex(ValueError, "version"):
                extract(original, html_text_version="unsupported")


if __name__ == "__main__":
    unittest.main()
