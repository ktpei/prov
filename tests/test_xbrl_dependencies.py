import unittest

from provenance.xbrl_dependencies import inspect_xml_references


class XbrlDependencyReferences(unittest.TestCase):
    def inspect(self, xml):
        return inspect_xml_references(
            xml.encode(),
            canonical_url="https://canonical.test/a/filing.htm",
            delivery_url="https://delivery.test/b/filing.htm",
        )

    def test_namespace_resolution_and_separate_bases(self):
        result = self.inspect("""<s:schema xmlns:s="http://www.w3.org/2001/XMLSchema">
          <s:import namespace="urn:domain" schemaLocation="taxonomy.xsd#part"/>
          <s:include schemaLocation="taxonomy.xsd#other"/>
        </s:schema>""")
        first, second = result["references"]
        self.assertEqual(first["canonical_url"], "https://canonical.test/a/taxonomy.xsd")
        self.assertEqual(first["delivery_url"], "https://delivery.test/b/taxonomy.xsd")
        self.assertEqual(first["canonical_fragment"], "part")
        self.assertEqual(first["expected_namespace"], "urn:domain")
        self.assertEqual(second["canonical_fragment"], "other")
        self.assertNotEqual(first["element_path"], second["element_path"])

    def test_inherited_xml_base_and_local_fragment(self):
        result = self.inspect("""<root xmlns:l="http://www.xbrl.org/2003/linkbase"
          xmlns:x="http://www.w3.org/1999/xlink" xml:base="sub/">
          <group xml:base="../schema.xsd"><l:loc x:href="#id"/></group>
        </root>""")
        ref = result["references"][0]
        self.assertEqual(ref["canonical_url"], "https://canonical.test/a/schema.xsd")
        self.assertEqual(ref["delivery_url"], "https://delivery.test/b/schema.xsd")
        self.assertEqual(ref["delivery_fragment"], "id")

    def test_unresolved_import_and_wrong_namespace_are_not_invented(self):
        result = self.inspect("""<root xmlns:s="http://www.w3.org/2001/XMLSchema">
          <s:import namespace="urn:missing"/><import schemaLocation="not-xsd"/>
        </root>""")
        self.assertEqual(len(result["references"]), 1)
        self.assertEqual(result["references"][0]["status"], "missing_location")
        self.assertNotIn("canonical_url", result["references"][0])

    def test_dtd_and_html_base_rejected(self):
        for xml in (
            '<!DOCTYPE root [<!ENTITY x "value">]><root>&x;</root>',
            '<html xmlns="http://www.w3.org/1999/xhtml"><head><base href="/"/></head></html>',
        ):
            with self.subTest(xml=xml), self.assertRaises(ValueError):
                self.inspect(xml)

    def test_non_http_or_credential_reference_rejected(self):
        for href in ("file:///private/data", "https://user:secret@example.test/a"):
            with self.subTest(href=href), self.assertRaises(ValueError):
                self.inspect(
                    '<schema xmlns="http://www.w3.org/2001/XMLSchema"><include schemaLocation="'
                    + href
                    + '"/></schema>'
                )

    def test_do_not_treat_namespace_uri_or_ordinary_href_as_dependency(self):
        self.assertEqual(
            self.inspect(
                '<r xmlns:s="https://example.test/vocabulary"><a href="not-a-taxonomy"/></r>'
            )["references"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
