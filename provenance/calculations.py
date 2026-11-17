"""Evidence-bound arithmetic relative to a trusted admission snapshot.

The constructor is a controller boundary, never a model-callable registration
tool. Structural validation here does not establish source or financial truth.
"""

import json
import re
from datetime import date

from provenance.calculation_numeric import (
    OPERATIONS,
    CalculationError,
    checked_response,
    decimal_input,
    evaluate_numeric,
)
from provenance.receipts import canonical, digest

POLICY = "financial-calculation-v1"
ATTRIBUTES = {
    "value",
    "scale",
    "unit",
    "entity",
    "metric",
    "period",
    "basis",
    "status",
    "scope",
    "measurement_precision",
}
COMMON = ("entity", "scope", "basis", "status")


def require(condition, code):
    if not condition:
        raise CalculationError(code)


def fields(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys), "invalid_record_fields")


def text(value):
    require(isinstance(value, str) and bool(value.strip()), "nonempty_text_required")


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "invalid_digest")


def copy_json(value):
    try:
        return json.loads(canonical(value))
    except (TypeError, ValueError) as exc:
        raise CalculationError("invalid_json_record") from exc


def iso_date(value):
    require(
        isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value),
        "invalid_period",
    )
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CalculationError("invalid_period") from exc


def validate_period(value):
    require(isinstance(value, dict), "invalid_period")
    if value.get("kind") == "instant":
        fields(value, ("kind", "date"))
        iso_date(value["date"])
    else:
        fields(value, ("kind", "start", "end"))
        require(value["kind"] == "duration", "invalid_period")
        require(iso_date(value["start"]) < iso_date(value["end"]), "invalid_period")


def validate_unit(value):
    fields(value, ("kind", "code", "rate_representation"))
    if value["kind"] in ("currency", "count"):
        text(value["code"])
        require(value["rate_representation"] == "none", "invalid_unit")
    elif value["kind"] == "dimensionless":
        require(
            value["code"] is None and value["rate_representation"] in ("fraction", "percent"),
            "invalid_unit",
        )
    else:
        require(value == unit("percentage_points"), "invalid_unit")


def unit(kind, representation="none"):
    return {"kind": kind, "code": None, "rate_representation": representation}


def validate_attribute(name, value):
    if name == "value":
        decimal_input(value)
    elif name == "scale":
        require(type(value) is int and -100 <= value <= 100, "invalid_scale")
    elif name == "unit":
        validate_unit(value)
    elif name == "entity":
        fields(value, ("scheme", "identifier"))
        for item in value.values():
            text(item)
    elif name == "metric":
        fields(value, ("namespace", "name", "role"))
        text(value["namespace"])
        text(value["name"])
        require(value["role"] in ("profit", "revenue", "rate", "other"), "invalid_metric_role")
    elif name == "period":
        validate_period(value)
    elif name == "basis":
        text(value)
    elif name == "status":
        require(value in ("actual", "guidance"), "invalid_status")
    elif name == "scope":
        fields(value, ("identity", "dimensions", "qualifiers", "complete"))
        text(value["identity"])
        require(value["complete"] is True, "incomplete_scope")
        require(isinstance(value["dimensions"], dict), "invalid_scope")
        for key, item in value["dimensions"].items():
            text(key)
            text(item)
        require(isinstance(value["qualifiers"], list), "invalid_scope")
        for item in value["qualifiers"]:
            text(item)
        require(len(set(value["qualifiers"])) == len(value["qualifiers"]), "invalid_scope")
    else:
        fields(value, ("kind", "value"))
        require(
            value["kind"] == "decimal_places" and type(value["value"]) is int,
            "invalid_measurement_precision",
        )


def validate_evidence(record, run_id):
    fields(
        record,
        (
            "run_id",
            "evidence_id",
            "kind",
            "source",
            "reader",
            "read_receipt",
            "delivery",
            "quarantined",
            "support",
            "attributes",
        ),
    )
    require(record["run_id"] == run_id, "cross_run_evidence")
    text(record["evidence_id"])
    require(
        record["kind"] in ("text_span", "table_cell_group", "xbrl_occurrence"),
        "invalid_evidence_kind",
    )
    require(
        record["delivery"] == "complete" and record["quarantined"] is False, "ineligible_evidence"
    )
    fields(record["source"], ("id", "original_sha256", "extracted_sha256"))
    text(record["source"]["id"])
    sha(record["source"]["original_sha256"])
    sha(record["source"]["extracted_sha256"])
    fields(record["reader"], ("name", "version"))
    for item in record["reader"].values():
        text(item)
    fields(record["read_receipt"], ("id", "sha256"))
    text(record["read_receipt"]["id"])
    sha(record["read_receipt"]["sha256"])
    support = record["support"]
    require(isinstance(support, dict) and bool(support), "missing_support")
    for identifier, item in support.items():
        text(identifier)
        fields(item, ("role", "locator", "content"))
        for content in item.values():
            text(content)
    fields(record["attributes"], ATTRIBUTES)
    for name, attribute in record["attributes"].items():
        fields(attribute, ("state", "value", "origin", "support_refs"))
        require(
            attribute["origin"] in ("parser_produced", "model_proposed"), "invalid_attribute_origin"
        )
        refs = attribute["support_refs"]
        require(isinstance(refs, list) and bool(refs), "missing_attribute_support")
        for identifier in refs:
            text(identifier)
            require(identifier in support, "unknown_support_reference")
        require(len(set(refs)) == len(refs), "duplicate_support_reference")
        if attribute["state"] == "known":
            validate_attribute(name, attribute["value"])
        else:
            require(
                attribute["state"] == "unknown" and attribute["value"] is None,
                "invalid_unknown_attribute",
            )


def comparable_periods(left, right):
    require(left["kind"] == right["kind"], "incompatible_periods")
    if left == right:
        return "identical"
    if left["kind"] == "instant":
        return "instant_comparison"
    a, b = iso_date(left["start"]), iso_date(left["end"])
    c, d = iso_date(right["start"]), iso_date(right["end"])
    if b - a == d - c:
        return "equal_days"
    if all(item.day == 1 for item in (a, b, c, d)) and (
        (b.year - a.year) * 12 + b.month - a.month == (d.year - c.year) * 12 + d.month - c.month
    ):
        return "equal_calendar_months"
    raise CalculationError("incompatible_periods")


class CalculationLedger:
    """Trusted-snapshot constructor; never pass model-authored admission here."""

    def __init__(self, trusted_snapshot):
        snapshot = copy_json(trusted_snapshot)
        fields(snapshot, ("run_id", "admission_policy", "evidence"))
        text(snapshot["run_id"])
        text(snapshot["admission_policy"])
        require(isinstance(snapshot["evidence"], list), "invalid_evidence_inventory")
        evidence = {}
        for record in snapshot["evidence"]:
            validate_evidence(record, snapshot["run_id"])
            identifier = record["evidence_id"]
            require(identifier not in evidence, "duplicate_evidence_id")
            evidence[identifier] = record
        self._snapshot, self._evidence, self._calculations = snapshot, evidence, {}
        self._snapshot_hash = digest(snapshot)

    def records(self):
        return copy_json(list(self._calculations.values()))

    def snapshot(self):
        return copy_json(self._snapshot)

    def _resolve(self, reference):
        fields(reference, ("kind", "id"))
        text(reference["id"])
        if reference["kind"] == "evidence":
            require(reference["id"] in self._evidence, "unknown_evidence_reference")
            record = self._evidence[reference["id"]]
            attributes = record["attributes"]
            require(
                all(
                    attributes[name]["state"] == "known"
                    for name in ATTRIBUTES - {"measurement_precision"}
                ),
                "unknown_required_attribute",
            )
            metadata = {name: attribute["value"] for name, attribute in attributes.items()}
            metric = {"kind": "reported", **metadata["metric"]}
            metadata["metric"] = metric
            numeric = {
                "value": metadata["value"],
                "scale": metadata["scale"],
                "rate_representation": metadata["unit"]["rate_representation"],
            }
            return record, metadata, numeric, 0, [reference["id"]]
        require(reference["kind"] == "calculation", "invalid_reference_kind")
        require(reference["id"] in self._calculations, "unknown_calculation_reference")
        record = self._calculations[reference["id"]]
        metadata = record["result_metadata"]
        require(metadata["period"]["kind"] != "comparison", "comparison_operand_unsupported")
        numeric = {
            "value": record["numeric"]["precision_result"],
            "scale": 0,
            "rate_representation": metadata["unit"]["rate_representation"],
        }
        return record, metadata, numeric, record["depth"], record["evidence_ids"]

    def calculate(self, operation, operand_refs, output_unit, rounding_policy):
        require(isinstance(operation, str) and operation in OPERATIONS, "unsupported_operation")
        require(isinstance(operand_refs, list), "invalid_operands")
        require(
            2 <= len(operand_refs) <= 32 if operation == "add" else len(operand_refs) == 2,
            "operand_count",
        )
        validate_unit(output_unit)
        refs = copy_json(operand_refs)
        resolved = [self._resolve(reference) for reference in refs]
        if operation == "add":
            require(len({canonical(ref) for ref in refs}) == len(refs), "duplicate_operand")
        metadata = [item[1] for item in resolved]
        first = metadata[0]
        for field in COMMON:
            require(all(item[field] == first[field] for item in metadata), "incompatible_" + field)
        require(
            all(
                (item["unit"]["kind"], item["unit"]["code"])
                == (first["unit"]["kind"], first["unit"]["code"])
                for item in metadata
            ),
            "incompatible_unit",
        )
        metric_hashes = [digest(item["metric"]) for item in metadata]
        if operation in (
            "add",
            "subtract",
            "relative_growth_percent",
            "percentage_point_difference",
        ):
            require(len(set(metric_hashes)) == 1, "incompatible_metric")
        if operation in ("add", "ratio", "margin_percent"):
            require(
                all(item["period"] == first["period"] for item in metadata), "incompatible_periods"
            )
            period_rule = "identical"
        else:
            period_rule = comparable_periods(first["period"], metadata[1]["period"])
        if operation == "margin_percent":
            require(
                first["unit"]["kind"] == "currency"
                and [item["metric"]["role"] for item in metadata] == ["profit", "revenue"],
                "invalid_margin_roles",
            )
        if operation == "percentage_point_difference":
            require(first["unit"]["kind"] == "dimensionless", "rate_operands_required")
        derived_unit = copy_json(first["unit"])
        if operation == "ratio":
            derived_unit = unit("dimensionless", "fraction")
        elif operation in ("margin_percent", "relative_growth_percent"):
            derived_unit = unit("dimensionless", "percent")
        elif operation == "percentage_point_difference":
            derived_unit = unit("percentage_points")
        elif derived_unit["kind"] == "dimensionless":
            derived_unit["rate_representation"] = "percent"
        require(output_unit == derived_unit, "output_unit_mismatch")
        depth = max(item[3] for item in resolved) + 1
        require(depth <= 16, "calculation_depth_limit")
        numeric = evaluate_numeric(operation, [item[2] for item in resolved], rounding_policy)
        period = first["period"]
        if operation == "relative_growth_percent" or first["period"] != metadata[-1]["period"]:
            period = {
                "kind": "comparison",
                "current": first["period"],
                "comparison": metadata[1]["period"],
            }
        metric = {
            "kind": "derived",
            "operation": operation,
            "operand_metrics": metric_hashes,
            "role": "rate"
            if operation in ("ratio", "margin_percent", "relative_growth_percent")
            else "other",
        }
        record = {
            "policy": POLICY,
            "run_id": self._snapshot["run_id"],
            "admission_policy": self._snapshot["admission_policy"],
            "admission_sha256": self._snapshot_hash,
            "request": {
                "operation": operation,
                "operand_refs": refs,
                "output_unit": output_unit,
                "rounding_policy": rounding_policy,
            },
            "operand_hashes": [digest(item[0]) for item in resolved],
            "depth": depth,
            "evidence_ids": sorted({identifier for item in resolved for identifier in item[4]}),
            "checks": {
                "period_rule": period_rule,
                "common_context_sha256": digest({key: first[key] for key in COMMON}),
                "like_units": True,
                "metric_rule": "ordered_ratio_roles"
                if operation in ("ratio", "margin_percent")
                else "equal_metric",
            },
            "result_metadata": {
                **{key: first[key] for key in COMMON},
                "metric": metric,
                "period": period,
                "unit": derived_unit,
            },
            "numeric": numeric,
            "validation": "Arithmetic and compatibility relative to trusted admission; not independent financial verification",
        }
        record["calculation_id"] = "calculation:" + digest(record)
        record = checked_response(record)
        self._calculations[record["calculation_id"]] = record
        return copy_json(record)


def replay_calculations(trusted_snapshot, records):
    """Rebuild entire records in order, never trust saved checks or display values."""
    require(isinstance(records, list), "invalid_calculation_inventory")
    ledger = CalculationLedger(trusted_snapshot)
    seen = set()
    for record in records:
        require(
            isinstance(record, dict) and isinstance(record.get("request"), dict),
            "invalid_calculation_record",
        )
        request = record["request"]
        fields(request, ("operation", "operand_refs", "output_unit", "rounding_policy"))
        rebuilt = ledger.calculate(**request)
        require(canonical(rebuilt) == canonical(record), "calculation_replay_mismatch")
        require(rebuilt["calculation_id"] not in seen, "duplicate_calculation_record")
        seen.add(rebuilt["calculation_id"])
    return ledger
