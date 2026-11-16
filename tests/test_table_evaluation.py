"""Frozen development packet positives and meaningful wrong-association negatives."""

import copy
import json
import unittest
from pathlib import Path

from provenance.table_evaluation import grade_table_packet
from provenance.table_structure import extract_html_tables

ROOT = Path(__file__).resolve().parents[1]


class TableEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sidecar = extract_html_tables(
            ROOT / "data/cloudflare-2024-q3/originals/cloudflare-q3-2024-release.html"
        )
        cls.fixtures = json.loads((ROOT / "eval/table-evidence-fixtures.json").read_text())[
            "fixtures"
        ]
        cls.cells = {
            c["id"]: c for t in cls.sidecar["tables"] for r in t["rows"] for c in r["cells"]
        }

    def packet(self, fixture):
        return {
            **{
                k: fixture[k]
                for k in ("source_id", "original_sha256", "sidecar_version", "table_id")
            },
            "cells": [copy.deepcopy(self.cells[k]) for k in fixture["expected_cells"]],
            "components": copy.deepcopy(fixture["required_components"]),
            "typed_values": dict(fixture["expected_typed_values"]),
        }

    def test_complete_frozen_packets_pass_and_every_missing_component_fails(self):
        for fixture in self.fixtures:
            packet = self.packet(fixture)
            with self.subTest(fixture=fixture["id"]):
                self.assertTrue(
                    grade_table_packet(fixture, self.sidecar, packet)["complete_packet_passed"]
                )
            for role in fixture["required_components"]:
                missing = copy.deepcopy(packet)
                missing["components"].pop(role)
                self.assertFalse(
                    grade_table_packet(fixture, self.sidecar, missing)["complete_packet_passed"]
                )

    def test_same_value_wrong_table_and_missing_split_sign_fail(self):
        fixture = self.fixtures[0]
        for substitute in ["table-12-r7-c10", "table-8-r31-c6", "table-8-r32-c2"]:
            packet = self.packet(fixture)
            packet["components"]["value_sign"][0] = substitute
            packet["cells"].append(copy.deepcopy(self.cells[substitute]))
            self.assertFalse(
                grade_table_packet(fixture, self.sidecar, packet)["complete_packet_passed"]
            )
        packet = self.packet(fixture)
        packet["cells"] = [c for c in packet["cells"] if c["id"] != "table-8-r31-c3"]
        self.assertFalse(
            grade_table_packet(fixture, self.sidecar, packet)["complete_packet_passed"]
        )

    def test_wrong_period_and_per_share_scale_fail(self):
        fixture = self.fixtures[1]
        packet = self.packet(fixture)
        packet["components"]["period_duration"] = ["table-9-r3-c10"]
        self.assertFalse(
            grade_table_packet(fixture, self.sidecar, packet)["complete_packet_passed"]
        )
        fixture = self.fixtures[3]
        packet = self.packet(fixture)
        packet["typed_values"]["value"] = "-40"
        self.assertFalse(
            grade_table_packet(fixture, self.sidecar, packet)["complete_packet_passed"]
        )

    def test_fabricated_locations_source_and_oversized_packet_fail(self):
        fixture = self.fixtures[0]
        for mutation in ("location", "source", "oversized", "duplicate", "extra_claim"):
            packet = self.packet(fixture)
            if mutation == "location":
                packet["cells"][0]["original_location"]["line"] += 1
            elif mutation == "source":
                packet["source_id"] = "cloudflare-q3-2024-filing"
            elif mutation == "duplicate":
                packet["cells"].append(packet["cells"][0])
            elif mutation == "extra_claim":
                packet["typed_values"]["unsupported_metric"] = "999"
            else:
                packet["unrelated_padding"] = "x" * fixture["max_packet_characters"]
            self.assertFalse(
                grade_table_packet(fixture, self.sidecar, packet)["complete_packet_passed"]
            )

    def test_boolean_geometry_and_oversized_valid_cell_packet_fail(self):
        fixture = self.fixtures[0]
        packet = self.packet(fixture)
        packet["cells"][0]["row_span"] = True
        self.assertFalse(
            grade_table_packet(fixture, self.sidecar, packet)["complete_packet_passed"]
        )
        packet = self.packet(fixture)
        packet["cells"] = [
            copy.deepcopy(c)
            for c in self.cells.values()
            if c["id"].startswith(fixture["table_id"] + "-")
        ]
        result = grade_table_packet(fixture, self.sidecar, packet)
        self.assertTrue(result["cell_provenance_valid"])
        self.assertFalse(result["within_size_limit"])
        self.assertFalse(result["complete_packet_passed"])

    def test_sidecar_or_fixture_drift_is_not_silently_scored(self):
        fixture = copy.deepcopy(self.fixtures[0])
        fixture["expected_cells"]["table-8-r31-c2"]["text"] = "111884"
        with self.assertRaisesRegex(ValueError, "differs"):
            grade_table_packet(fixture, self.sidecar, self.packet(fixture))
