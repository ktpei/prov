"""Independent expectations for the optional fixed dimensional fixture."""

import unittest

from probe import observe


class DimensionalContextAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = observe()

    def test_all_occurrences_and_contexts_preserved(self):
        self.assertEqual(len(self.result["facts"]), 13)
        self.assertEqual(len(self.result["contexts"]), 10)
        self.assertTrue(all(f["validation_state"] >= 4 for f in self.result["facts"]))
        assets = [
            f for f in self.result["facts"] if f["concept"] == "{urn:synthetic:finance}Assets"
        ]
        self.assertEqual(len(assets), 9)
        self.assertEqual({f["value"] for f in assets}, {"-12000"})
        self.assertEqual(len({f["context_id"] for f in assets}), 9)

    def test_explicit_members_use_expanded_names(self):
        for context, member in (("north", "North"), ("north-alias", "North"), ("south", "South")):
            dimensions = self.result["contexts"][context]["reported_dimensions"]
            self.assertEqual(len(dimensions), 1)
            self.assertEqual(dimensions[0]["dimension"], "{urn:synthetic:finance}RegionAxis")
            self.assertEqual(dimensions[0]["member"], "{urn:synthetic:finance}" + member)
            self.assertEqual(dimensions[0]["location"], "segment")
            self.assertEqual(dimensions[0]["kind"], "explicit")

    def test_typed_members_preserve_value_and_source(self):
        for context, value in (("typed", "A001"), ("typed-same", "A001"), ("typed-other", "A002")):
            dimensions = self.result["contexts"][context]["reported_dimensions"]
            self.assertEqual(len(dimensions), 1)
            self.assertEqual(dimensions[0]["dimension"], "{urn:synthetic:finance}AccountAxis")
            self.assertEqual(
                dimensions[0]["typed_member_name"], "{urn:synthetic:finance}AccountCode"
            )
            self.assertEqual(dimensions[0]["typed_value"], value)
            self.assertIn(">" + value + "</", dimensions[0]["typed_member"]["canonical_xml"])
            self.assertEqual(dimensions[0]["kind"], "typed")

    def test_residual_context_content_is_not_dropped(self):
        for context, value in (("residual", "budget"), ("residual-other", "actual")):
            record = self.result["contexts"][context]
            self.assertEqual(record["reported_dimensions"], [])
            self.assertEqual(record["non_dimensional_content"]["segment"], [])
            scenario = record["non_dimensional_content"]["scenario"]
            self.assertEqual(len(scenario), 1)
            self.assertIn(">" + value + "</", scenario[0]["canonical_xml"])

    def test_equal_contexts_group_without_collapsing_other_scopes(self):
        self.assertEqual(
            self.result["duplicate_groups"],
            [["north-alias-fact", "north-fact"], ["typed-fact", "typed-same-fact"]],
        )
        self.assertEqual(self.result["diagnostics"], [("WARNING", "arelle:duplicateFacts")])

    def test_no_default_or_dependency_claim_beyond_fixture(self):
        self.assertEqual(self.result["taxonomy_dimension_defaults"], {})
        self.assertEqual(len(self.result["loaded_document_sha256"]), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
