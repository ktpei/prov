"""Evaluator-only connected table packets; no labels enter extraction or retrieval."""

import json
from decimal import Decimal, InvalidOperation


def _typed_equal(actual, expected):
    if isinstance(actual, bool):
        return False
    try:
        target = Decimal(expected)
    except InvalidOperation:
        return actual == expected
    try:
        value = Decimal(str(actual))
    except InvalidOperation:
        return False
    return value.is_finite() and value == target


def grade_table_packet(fixture, sidecar, packet):
    """Grade explicit component associations against a frozen development fixture.

    This checks a supplied packet, not whether an agent retrieved or understood it.
    Fixture labels and sidecar authenticity must be controlled by the evaluator.
    """
    if (
        sidecar["original_sha256"] != fixture["original_sha256"]
        or sidecar["version"] != fixture["sidecar_version"]
    ):
        raise ValueError("Fixture/sidecar identity mismatch")
    tables = {table["id"]: table for table in sidecar["tables"]}
    if fixture["table_id"] not in tables:
        raise ValueError("Fixture table is absent")
    cells = {
        cell["id"]: cell for row in tables[fixture["table_id"]]["rows"] for cell in row["cells"]
    }
    for identity, expected in fixture["expected_cells"].items():
        if identity not in cells or json.dumps(
            {k: cells[identity].get(k) for k in expected}, sort_keys=True, allow_nan=False
        ) != json.dumps(expected, sort_keys=True, allow_nan=False):
            raise ValueError("Frozen fixture cell differs from sidecar")

    result = {
        "fixture_id": fixture["id"],
        "status": "invalid_packet",
        "identity_valid": False,
        "within_size_limit": False,
        "cell_provenance_valid": False,
        "component_matches": {},
        "typed_value_matches": {},
        "complete_packet_passed": False,
        "limitations": "Structural fixture grading only; no agent execution or human validation established.",
    }
    if not isinstance(packet, dict) or set(packet) != {
        "source_id",
        "original_sha256",
        "sidecar_version",
        "table_id",
        "cells",
        "components",
        "typed_values",
    }:
        return result
    try:
        size = len(json.dumps(packet, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError):
        return result
    result["packet_characters"] = size
    result["within_size_limit"] = size <= fixture["max_packet_characters"]
    result["identity_valid"] = all(
        packet.get(key) == fixture[key]
        for key in ("source_id", "original_sha256", "sidecar_version", "table_id")
    )
    supplied = packet.get("cells")
    if not isinstance(supplied, list) or any(not isinstance(cell, dict) for cell in supplied):
        return result
    ids = [cell.get("id") for cell in supplied]
    if any(not isinstance(identity, str) for identity in ids) or len(set(ids)) != len(ids):
        return result
    # Validate every included cell against this table, not just expected values.
    result["cell_provenance_valid"] = all(
        cell["id"] in cells
        and json.dumps(cell, sort_keys=True, allow_nan=False)
        == json.dumps(cells[cell["id"]], sort_keys=True, allow_nan=False)
        and cells[cell["id"]].get("visibility") != "explicitly_hidden"
        for cell in supplied
    )
    components = packet.get("components")
    values = packet.get("typed_values")
    if (
        not isinstance(components, dict)
        or not isinstance(values, dict)
        or set(components) != set(fixture["required_components"])
        or set(values) != set(fixture["expected_typed_values"])
    ):
        return result
    result["component_matches"] = {
        role: components.get(role) == expected and set(expected) <= set(ids)
        for role, expected in fixture["required_components"].items()
    }
    result["typed_value_matches"] = {
        key: _typed_equal(values.get(key), expected)
        for key, expected in fixture["expected_typed_values"].items()
    }
    result["status"] = "scored"
    result["complete_packet_passed"] = (
        result["identity_valid"]
        and result["within_size_limit"]
        and result["cell_provenance_valid"]
        and all(result["component_matches"].values())
        and all(result["typed_value_matches"].values())
    )
    return result
