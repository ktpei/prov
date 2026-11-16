"""Expected dimensional validation outcomes, independent of observed diagnostics."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from matrix import CASES, HERE, matrix

AXIS = "{urn:synthetic:applicability}RegionAxis"
DEFAULT = "{urn:synthetic:applicability}AllRegions"
PRIMARY_ERROR = "xbrldie:PrimaryItemDimensionallyInvalidError"


class ApplicabilityAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = matrix()
        cls.cases = {case["case"]: case for case in cls.result["cases"]}

    def test_changed_child_revision_rejects_combined_record(self):
        changed = dict(self.result["cases"][0], driver_sha256="0" * 64)
        with patch(
            "matrix.subprocess.run", return_value=SimpleNamespace(stdout=json.dumps(changed))
        ):
            with self.assertRaisesRegex(ValueError, "Child revision differs"):
                matrix()

    def test_between_child_input_change_rejects_combined_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            for name in ("omitted.xhtml", "taxonomy.xsd", "definition.xml", "manifest.json"):
                (temporary / name).write_bytes((HERE / name).read_bytes())
            calls = iter(self.result["cases"])

            def changed_input(*args, **kwargs):
                case = next(calls)
                if case["case"] == "north":
                    with (temporary / "omitted.xhtml").open("ab") as handle:
                        handle.write(b" ")
                return SimpleNamespace(stdout=json.dumps(case))

            with (
                patch("matrix.HERE", temporary),
                patch("matrix.subprocess.run", side_effect=changed_input),
            ):
                with self.assertRaisesRegex(ValueError, "Matrix inputs changed"):
                    matrix()

    def test_complete_case_inventory_and_successes(self):
        self.assertEqual(set(self.cases), set(CASES))
        self.assertEqual(len(self.cases), 14)
        accepted = {name for name, case in self.cases.items() if case["accepted"]}
        self.assertEqual(
            accepted,
            {
                "omitted_default",
                "north",
                "north_in_scenario",
                "extra_scenario_axis",
                "residual_scenario",
            },
        )
        for name in accepted:
            self.assertEqual(self.cases[name]["diagnostics"], [])

    def test_required_errors_and_fact_attribution(self):
        required = {
            "explicit_default": "xbrldie:DefaultValueUsedInInstanceError",
            "undefined_member": "xbrldie:ExplicitMemberUndefinedQNameError",
            **{
                name: PRIMARY_ERROR
                for name in (
                    "unusable_south",
                    "extra_segment_axis",
                    "missing_default",
                    "default_outside_domain",
                    "scenario_without_default",
                    "declared_outside_domain",
                    "residual_segment",
                )
            },
        }
        for name, code in required.items():
            with self.subTest(case=name):
                case = self.cases[name]
                self.assertFalse(case["accepted"])
                self.assertIn(code, case["model_errors"])
                references = [
                    record for record in case["diagnostic_references"] if record["code"] == code
                ]
                self.assertTrue(references)
                self.assertTrue(
                    any(
                        ref["href"] == "omitted.xhtml#assets"
                        for record in references
                        for ref in record["references"]
                    )
                )

    def test_defaults_remain_separate_from_reported_dimensions(self):
        case = self.cases["omitted_default"]
        self.assertEqual(case["reported_dimensions"], {})
        self.assertEqual(case["taxonomy_defaults"], {AXIS: DEFAULT})
        self.assertEqual(self.cases["missing_default"]["taxonomy_defaults"], {})
        outside = self.cases["default_outside_domain"]
        self.assertEqual(outside["taxonomy_defaults"], {AXIS: DEFAULT})
        self.assertFalse(outside["accepted"])

    def test_container_identity_is_preserved(self):
        for name, location in (
            ("north", "segment"),
            ("north_in_scenario", "scenario"),
            ("scenario_without_default", "scenario"),
        ):
            case = self.cases[name]
            self.assertEqual(
                case["reported_dimensions"], {AXIS: "{urn:synthetic:applicability}North"}
            )
            self.assertEqual(case["reported_locations"], {AXIS: location})
        self.assertTrue(self.cases["north_in_scenario"]["accepted"])
        self.assertFalse(self.cases["scenario_without_default"]["accepted"])

    def test_invalid_dimensions_do_not_imply_parse_or_schema_failure(self):
        for case in self.cases.values():
            self.assertTrue(case["api_success"])
            self.assertEqual(case["fact_count"], 1)
            self.assertEqual(case["facts"][0]["value"], "100")
            self.assertGreaterEqual(case["facts"][0]["schema_validation_state"], 4)
            self.assertEqual(len(case["candidate_document_sha256"]), 9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
