"""Optional paired issuer assertions and comparison failure controls."""

import copy
import json
import unittest

from compare_sec_transforms import EXPECTATIONS, compare, verify


class SecTransformAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = compare()
        cls.expected = json.loads(EXPECTATIONS.read_text())

    def test_paired_acceptance(self):
        self.assertEqual(self.result["checks"]["verified_transformed_occurrences"], 12)
        self.assertEqual(self.result["checks"]["unchanged_occurrences"], 492)
        self.assertEqual(self.result["checks"]["all_schema_valid_occurrences"], 504)

    def test_diagnostics_are_stable_within_each_run(self):
        for condition in ("control", "candidate"):
            result = self.result[condition]
            self.assertEqual(
                result["initial_diagnostic_counts"], result["after_values_diagnostic_counts"]
            )
            self.assertEqual(result["initial_diagnostic_counts"], result["diagnostic_counts"])

    def test_only_explicit_plugin_and_transforms_registered(self):
        self.assertEqual(self.result["control"]["plugin_inventory"], {})
        self.assertEqual(self.result["control"]["registered_sec_transforms"], [])
        plugin = self.result["candidate"]["plugin_inventory"]
        self.assertEqual(list(plugin), ["SEC Inline Transforms"])
        self.assertEqual(plugin["SEC Inline Transforms"]["version"], "19.2")
        self.assertEqual(len(self.result["candidate"]["registered_sec_transforms"]), 18)

    def test_unaffected_value_mutation_is_rejected(self):
        changed = copy.deepcopy(self.result["candidate"])
        affected = {fact["id"] for fact in changed["affected_facts"]}
        next(fact for fact in changed["facts"] if fact["id"] not in affected)[
            "typed_value_sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Unaffected occurrence changed"):
            verify(self.result["control"], changed, self.expected)

    def test_context_mutation_is_rejected(self):
        changed = copy.deepcopy(self.result["candidate"])
        key = next(iter(changed["context_source_sha256"]))
        changed["context_source_sha256"][key] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Paired source/runtime inputs differ"):
            verify(self.result["control"], changed, self.expected)

    def test_changed_transformed_value_is_rejected(self):
        changed = copy.deepcopy(self.result["candidate"])
        changed["affected_facts"][0]["typed_value"] = "999"
        with self.assertRaisesRegex(ValueError, "Affected detail differs"):
            verify(self.result["control"], changed, self.expected)

    def test_duplicate_occurrence_drop_is_rejected(self):
        changed = copy.deepcopy(self.result["candidate"])
        changed["duplicate_groups"].pop(0)
        with self.assertRaisesRegex(ValueError, "duplicate group"):
            verify(self.result["control"], changed, self.expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
