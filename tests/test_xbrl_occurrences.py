import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from provenance.table_structure import extract_html_tables
from provenance.xbrl_occurrences import occurrence_sidecar

HEADER = '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:s="urn:synthetic"><body>'
FOOTER = "</body></html>"


def fact(identifier="f", content="12", extra="", tag="nonFraction"):
    return (
        f'<ix:{tag} id="{identifier}" name="s:Amount" contextRef="c" {extra}>{content}</ix:{tag}>'
    )


def narrative(identifier="f", content="text", extra=""):
    return fact(identifier, content, extra, tag="nonNumeric")


class XbrlOccurrences(unittest.TestCase):
    def extract(self, body, *, prefix="", empty_tables=False):
        raw = (prefix + HEADER + body + FOOTER).encode()
        if empty_tables:
            tables = {
                "version": "native-html-tables-v2",
                "original_sha256": hashlib.sha256(raw).hexdigest(),
                "tables": [],
            }
        else:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "source.html"
                path.write_bytes(raw)
                tables = extract_html_tables(path)
        table_raw = json.dumps(tables).encode()
        return raw, table_raw, occurrence_sidecar(raw, table_raw)

    def test_exact_cell_mapping_and_many_occurrences(self):
        raw, table_raw, result = self.extract(
            "<table><tr><td>" + fact("a") + fact("b") + "</td></tr></table>"
        )
        a, b = result["facts"]
        self.assertEqual(a["table_mapping"], b["table_mapping"])
        self.assertEqual(a["source_disposition"], "cell_mapped")
        self.assertEqual(a["expanded_concept"], "{urn:synthetic}Amount")
        self.assertEqual(raw[a["byte_start"] : a["byte_end"]], fact("a").encode())
        self.assertEqual(a["source_bytes_sha256"], hashlib.sha256(fact("a").encode()).hexdigest())
        self.assertEqual(result["table_sidecar_sha256"], hashlib.sha256(table_raw).hexdigest())

    def test_nested_fact_and_no_cell_text_block_are_not_flattened(self):
        _, _, result = self.extract(
            fact("outer", "<table><tr><td>" + fact("inner") + "</td></tr></table>")
        )
        outer, inner = result["facts"]
        self.assertEqual(outer["source_disposition"], "outside_table")
        self.assertEqual(inner["ancestor_fact_ids"], ["outer"])
        self.assertEqual(inner["source_disposition"], "cell_mapped")

    def test_hidden_fact_and_orphan_hidden_continuation_are_explicit(self):
        _, _, result = self.extract(
            "<ix:hidden>"
            + fact()
            + '<ix:continuation id="orphan">text</ix:continuation></ix:hidden>'
        )
        self.assertTrue(result["facts"][0]["ix_hidden"])
        self.assertEqual(result["facts"][0]["source_disposition"], "explicitly_hidden")
        self.assertEqual(
            result["continuations"][0]["continuation_issues"], ["orphan", "inside_ix_hidden"]
        )

    def test_offsets_preserve_bom_unicode_crlf_cr_and_quoted_greater_than(self):
        body = (
            "é\r\ntext\r<table><tr><td>"
            + fact(extra='data-note=">"')
            + '<ix:nonFraction id="empty" name="s:Amount" /></td></tr></table>'
        )
        raw, _, result = self.extract(body, prefix="\ufeff")
        first, empty = result["facts"]
        self.assertEqual(
            raw[first["byte_start"] : first["byte_end"]], fact(extra='data-note=">"').encode()
        )
        self.assertEqual(
            raw[empty["byte_start"] : empty["byte_end"]],
            b'<ix:nonFraction id="empty" name="s:Amount" />',
        )
        text = raw[: first["byte_start"]].decode()
        self.assertEqual(
            first["start_location"],
            {"line": text.count("\n") + 1, "column": len(text.rsplit("\n", 1)[-1])},
        )

    def test_physical_continuation_nesting_is_not_link_chain(self):
        body = narrative("a", extra='continuedAt="ca"') + narrative("b", extra='continuedAt="cb"')
        body += (
            '<ix:continuation id="ca">A<ix:continuation id="cb">B'
            + narrative("inside")
            + "</ix:continuation></ix:continuation>"
        )
        _, _, result = self.extract(body)
        self.assertEqual([f["id"] for f in result["facts"]], ["a", "b", "inside"])
        self.assertEqual(result["facts"][2]["ancestor_continuation_ids"], ["cb", "ca"])
        self.assertEqual([f["id"] for f in result["facts"][0]["continuation_fragments"]], ["ca"])
        self.assertEqual(result["continuations"][1]["referenced_by"], "b")

    def test_invalid_continuation_relations_reject(self):
        examples = [
            narrative(extra='continuedAt="missing"'),
            narrative(extra='continuedAt="f"'),
            narrative(extra='continuedAt="a"') + '<span id="a"/>',
            narrative("a", extra='continuedAt="c"')
            + narrative("b", extra='continuedAt="c"')
            + '<ix:continuation id="c"/>',
            narrative(content='<ix:continuation id="c"/>', extra='continuedAt="c"'),
            narrative(extra='continuedAt="a"')
            + '<ix:continuation id="a" continuedAt="b"/><ix:continuation id="b" continuedAt="a"/>',
        ]
        for body in examples:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.extract(body)

    def test_html_xml_geometry_disagreement_rejects(self):
        examples = [
            '<table><tr><td id="a"><td id="b">x</td>' + fact() + "</td></tr></table>",
            "<table><tr><tr><td>" + fact() + "</td></tr></tr></table>",
            '<table xmlns="urn:foreign"><tr><td>' + fact() + "</td></tr></table>",
            '<h:table xmlns:h="http://www.w3.org/1999/xhtml"><h:tr><h:td>'
            + fact()
            + "</h:td></h:tr></h:table>",
            "<template>" + fact() + "</template>",
        ]
        for body in examples:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.extract(body, empty_tables=True)

    def test_missing_cell_keeps_explicit_unmapped_disposition(self):
        _, _, result = self.extract(
            "<table><tr><td>" + fact() + "</td></tr></table>", empty_tables=True
        )
        self.assertEqual(result["facts"][0]["source_disposition"], "cell_unmapped")

    def test_sidecar_hash_and_duplicate_positions_reject(self):
        raw, table_raw, _ = self.extract("<table><tr><td>" + fact() + "</td></tr></table>")
        tables = json.loads(table_raw)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            occurrence_sidecar(raw + b" ", table_raw)
        tables["tables"][0]["rows"][0]["cells"].append(
            copy.deepcopy(tables["tables"][0]["rows"][0]["cells"][0])
        )
        with self.assertRaisesRegex(ValueError, "Ambiguous cell"):
            occurrence_sidecar(raw, json.dumps(tables).encode())

    def test_raw_text_and_unsupported_inline_types_reject(self):
        for body in (
            "<title>" + fact() + "</title>",
            "<ix:tuple/>",
            '<old:nonFraction xmlns:old="http://www.xbrl.org/2008/inlineXBRL"/>',
        ):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.extract(body, empty_tables=True)

    def test_unrelated_html_attribute_cannot_reference_continuation(self):
        _, _, result = self.extract(
            '<span id="unrelated" continuedAt="c"/><ix:continuation id="c">text</ix:continuation>'
        )
        self.assertIsNone(result["continuations"][0]["referenced_by"])
        self.assertEqual(result["continuations"][0]["continuation_issues"], ["orphan"])
        with self.assertRaisesRegex(ValueError, "unsupported Inline XBRL source"):
            self.extract(fact(extra='continuedAt="c"') + '<ix:continuation id="c"/>')

    def test_duplicate_ids_and_dtd_reject(self):
        with self.assertRaisesRegex(ValueError, "duplicate source ID"):
            self.extract(fact("same") + fact("same"))
        with self.assertRaisesRegex(ValueError, "DTD unsupported"):
            self.extract(fact(), prefix="<!DOCTYPE html>")


if __name__ == "__main__":
    unittest.main()
