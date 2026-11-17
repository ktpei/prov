"""Optional real-issuer and Arelle-value assertions for the integrated sidecar."""

import unittest
from collections import Counter
from datetime import timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from arelle.ModelValue import DateTime, gMonthDay, gYear, qname

from eval.scripts.build_xbrl_fact_report import build
from provenance.xbrl_facts import typed_value


class FactSidecarAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build()
        cls.facts = {fact["id"]: fact for fact in cls.result["facts"]}

    def test_complete_occurrence_context_unit_and_group_inventories(self):
        result = self.result
        self.assertEqual(len(result["facts"]), 504)
        self.assertEqual(len(result["contexts"]), 71)
        self.assertEqual(len(result["units"]), 5)
        self.assertEqual(len(result["duplicate_groups"]), 80)
        self.assertEqual(
            Counter(f["source_occurrence"]["source_disposition"] for f in result["facts"]),
            {"cell_mapped": 420, "outside_table": 77, "explicitly_hidden": 7},
        )
        self.assertTrue(all(f["validation_state"] >= 4 for f in result["facts"]))

    def test_synthetic_inconsistent_group_is_quarantined_without_dropping_facts(self):
        from arelle.ValidateDuplicateFacts import getDuplicateFactSets

        def injected(facts, includeSingles=False):
            groups = list(getDuplicateFactSets(facts, includeSingles=includeSingles))
            return [
                SimpleNamespace(
                    facts=groups[0].facts,
                    areAllComplete=False,
                    areAllConsistent=False,
                    areAnyInconsistent=True,
                ),
                *groups[1:],
            ]

        with patch("arelle.ValidateDuplicateFacts.getDuplicateFactSets", side_effect=injected):
            result = build()
        conflicts = {
            identifier
            for group in result["duplicate_groups"]
            if group["inconsistent"]
            for identifier in group["occurrences"]
        }
        self.assertTrue(conflicts)
        self.assertEqual(len(result["facts"]), 504)
        self.assertEqual(
            {
                fact["id"]
                for fact in result["facts"]
                if fact["disposition"] == "quarantined_inconsistent_duplicate"
            },
            conflicts,
        )
        self.assertTrue(
            all(fact["financial_correctness"] == "unverified" for fact in result["facts"])
        )

    def test_all_observed_value_classes_have_distinct_representations(self):
        self.assertEqual(
            Counter(f["value"]["kind"] for f in self.facts.values()),
            {
                "decimal": 446,
                "string": 38,
                "boolean": 10,
                "integer": 4,
                "nil": 2,
                "enumeration_set": 1,
                "gMonthDay": 1,
                "gYear": 1,
                "date_time": 1,
            },
        )
        nil_ids = {
            "F_4887bb55-57d5-47ad-a9e1-931d12ad9e68",
            "F_d6d79b3b-30b4-41ee-97c3-4c6898ab25cf",
        }
        self.assertEqual({f["id"] for f in self.facts.values() if f["nil"]}, nil_ids)
        for identifier in nil_ids:
            self.assertEqual(self.facts[identifier]["value"], {"kind": "nil", "value": None})

    def test_independent_enumeration_and_temporal_expectations(self):
        enum = self.facts["F_1a451104-a7d9-405d-b441-530fcfe0e294"]["value"]
        self.assertEqual(
            enum["members"],
            [
                {
                    "kind": "qname",
                    "namespace_uri": "http://odfl.com/20250630",
                    "local_name": "PresidentAndCEOMember",
                }
            ],
        )
        self.assertEqual(
            self.facts["F_45d4c880-c239-41e2-b9e1-45132e47b986"]["value"],
            {"kind": "gMonthDay", "month": 12, "day": 31, "timezone_offset_seconds": None},
        )
        self.assertEqual(
            self.facts["F_5825572e-2bd0-431c-8846-20b69c5d90e9"]["value"],
            {"kind": "gYear", "year": "2025", "timezone_offset_seconds": None},
        )
        date = self.facts["F_d3a7cf58-f925-47be-9a85-ae3f28eb6b32"]["value"]
        self.assertTrue(date["date_only"])
        self.assertEqual((date["year"], date["month"], date["day"]), (2025, 6, 30))
        self.assertIsNone(date["timezone_offset_seconds"])

    def test_independently_derived_scaling_sign_zero_and_context(self):
        cases = [
            ("F_e5f67804-d61f-4693-b6b5-bc0dc62a76e8", "24,057", "3", None, "-3", "24057000"),
            ("F_7a65e687-9aaa-43aa-9c21-a2ca35d20104", "200.0", "6", None, "-5", "200000000"),
            ("F_a0b45199-73b0-42c2-a6fe-77fdc1e60302", "1,357", "3", "-", "-3", "-1357000"),
            ("F_cafba24e-d3c2-4afd-aa16-d0e27d4640dc", "—", "3", None, "-3", "0"),
        ]
        for identifier, text, scale, sign, decimals, expected in cases:
            with self.subTest(identifier=identifier):
                fact = self.facts[identifier]
                self.assertEqual(fact["assembled_pretransform_text"], text)
                self.assertEqual(fact["reported_attributes"].get("scale"), scale)
                self.assertEqual(fact["reported_attributes"].get("sign"), sign)
                self.assertEqual(fact["reported_attributes"].get("decimals"), decimals)
                self.assertEqual(Decimal(fact["value"]["value"]), Decimal(expected))
                self.assertEqual(fact["unit_id"], "U_USD")
                self.assertFalse(fact["nil"])
        context = self.result["contexts"]["C_8e2dae44-e530-48da-b216-8993e0b6617b"]
        self.assertEqual(context["reported_period"], {"instant": "2025-06-30"})
        self.assertEqual(context["normalized_period"], {"instant": "2025-07-01T00:00:00"})
        self.assertEqual(context["reported_dimensions"], [])

    def test_reported_dimensions_do_not_absorb_taxonomy_defaults(self):
        self.assertEqual(len(self.result["taxonomy_defaults"]), 21)
        self.assertEqual(
            sum(len(c["reported_dimensions"]) for c in self.result["contexts"].values()), 67
        )
        for default in self.result["taxonomy_defaults"].values():
            self.assertTrue(default["supporting_relationships"])
            for relationship in default["supporting_relationships"]:
                self.assertEqual(
                    relationship["document_sha256"],
                    self.result["loaded_document_sha256"][relationship["document_uri"]],
                )
        self.assertTrue(all(c["boundary_verified"] for c in self.result["contexts"].values()))

    def test_arelle_datetime_retains_fraction_and_partial_dates_have_no_invented_fields(self):
        value = DateTime(
            2025, 6, 30, 12, 34, 56, 123456, tzinfo=timezone(-timedelta(hours=5, minutes=30))
        )
        record = typed_value(value)
        self.assertEqual(record["microsecond"], 123456)
        self.assertEqual(record["timezone_offset_seconds"], -19800)
        self.assertNotIn("month", typed_value(gYear(-2025)))
        self.assertNotIn("year", typed_value(gMonthDay(12, 31)))
        with self.assertRaisesRegex(ValueError, "schema-confirmed"):
            typed_value([qname("urn:sample", "member")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
