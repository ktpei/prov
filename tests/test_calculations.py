"""Synthetic trusted-admission fixtures; not real source/semantic acceptance."""

import copy
import unittest

from provenance.calculation_numeric import CalculationError
from provenance.calculations import CalculationLedger, replay_calculations, unit
from provenance.receipts import digest

USD = {"kind": "currency", "code": "USD", "rate_representation": "none"}
PERCENT = unit("dimensionless", "percent")
FRACTION = unit("dimensionless", "fraction")


def evidence(identifier, value, *, year=2024, metric="revenue", role="revenue", units=None):
    values = {
        "value": value,
        "scale": 0,
        "unit": units or USD,
        "entity": {"scheme": "synthetic", "identifier": "acme"},
        "metric": {"namespace": "synthetic", "name": metric, "role": role},
        "period": {"kind": "duration", "start": f"{year}-01-01", "end": f"{year + 1}-01-01"},
        "basis": "synthetic-GAAP",
        "status": "actual",
        "scope": {"identity": "consolidated", "dimensions": {}, "qualifiers": [], "complete": True},
        "measurement_precision": {"kind": "decimal_places", "value": 0},
    }
    return {
        "run_id": "synthetic-run",
        "evidence_id": identifier,
        "kind": "text_span",
        "source": {"id": "acme", "original_sha256": "a" * 64, "extracted_sha256": "b" * 64},
        "reader": {"name": "synthetic-reader", "version": "v1"},
        "read_receipt": {"id": "read-" + identifier, "sha256": digest(values)},
        "delivery": "complete",
        "quarantined": False,
        "support": {
            name: {"role": name, "locator": identifier + ":" + name, "content": str(item)}
            for name, item in values.items()
        },
        "attributes": {
            name: {
                "state": "known",
                "value": copy.deepcopy(item),
                "origin": "parser_produced",
                "support_refs": [name],
            }
            for name, item in values.items()
        },
    }


def snapshot(*items):
    return {
        "run_id": "synthetic-run",
        "admission_policy": "synthetic-fixture-only-v1",
        "evidence": list(items),
    }


def ref(identifier, kind="evidence"):
    return {"kind": kind, "id": identifier}


def calc(ledger, operation, refs, output=USD, places=2):
    return ledger.calculate(operation, refs, output, {"decimal_places": places})


def attr(item, field, value):
    item["attributes"][field]["value"] = value


class CalculationLedgerTests(unittest.TestCase):
    def assert_error(self, code, callback):
        with self.assertRaises(CalculationError) as caught:
            callback()
        self.assertEqual(caught.exception.code, code)

    def test_current_prior_margin_chain_and_replay(self):
        trusted = snapshot(
            evidence("p24", "30", metric="profit", role="profit"),
            evidence("r24", "120"),
            evidence("p23", "20", year=2023, metric="profit", role="profit"),
            evidence("r23", "100", year=2023),
        )
        ledger = CalculationLedger(trusted)
        current = calc(ledger, "margin_percent", [ref("p24"), ref("r24")], PERCENT)
        prior = calc(ledger, "margin_percent", [ref("p23"), ref("r23")], PERCENT)
        self.assertEqual(current["result_metadata"]["metric"], prior["result_metadata"]["metric"])
        result = calc(
            ledger,
            "percentage_point_difference",
            [
                ref(current["calculation_id"], "calculation"),
                ref(prior["calculation_id"], "calculation"),
            ],
            unit("percentage_points"),
        )
        self.assertEqual(result["numeric"]["display_value"], "5.00")
        self.assertEqual(result["checks"]["period_rule"], "equal_calendar_months")
        self.assertEqual(result["result_metadata"]["period"]["kind"], "comparison")
        self.assertEqual(result["evidence_ids"], ["p23", "p24", "r23", "r24"])
        self.assertEqual(replay_calculations(trusted, ledger.records()).records(), ledger.records())
        self.assert_error(
            "comparison_operand_unsupported",
            lambda: calc(
                ledger, "ratio", [ref(result["calculation_id"], "calculation")] * 2, FRACTION
            ),
        )

    def test_unknown_attributes_and_model_proposed_origin_preserved(self):
        for field in (
            "scope",
            "period",
            "value",
            "unit",
            "metric",
            "basis",
            "status",
            "entity",
            "scale",
        ):
            item = evidence("a", "10")
            item["attributes"][field].update(state="unknown", value=None)
            ledger = CalculationLedger(snapshot(item, evidence("b", "2")))
            self.assert_error(
                "unknown_required_attribute",
                lambda ledger=ledger: calc(ledger, "ratio", [ref("a"), ref("b")], FRACTION),
            )
        item = evidence("a", "10")
        item["attributes"]["measurement_precision"].update(state="unknown", value=None)
        item["attributes"]["value"]["origin"] = "model_proposed"
        ledger = CalculationLedger(snapshot(item, evidence("b", "2")))
        calc(ledger, "ratio", [ref("a"), ref("b")], FRACTION)
        self.assertEqual(
            ledger.snapshot()["evidence"][0]["attributes"]["value"]["origin"], "model_proposed"
        )

    def test_scope_currency_entity_basis_status_and_metric_reject(self):
        mutations = {
            "scope": {
                "identity": "segment",
                "dimensions": {"segment": "east"},
                "qualifiers": [],
                "complete": True,
            },
            "unit": {**USD, "code": "EUR"},
            "entity": {"scheme": "synthetic", "identifier": "other"},
            "basis": "non-GAAP",
            "status": "guidance",
            "metric": {"namespace": "another", "name": "revenue", "role": "revenue"},
        }
        for field, value in mutations.items():
            item = evidence("b", "2")
            attr(item, field, value)
            ledger = CalculationLedger(snapshot(evidence("a", "10"), item))
            self.assert_error(
                "incompatible_" + field,
                lambda ledger=ledger: calc(ledger, "subtract", [ref("a"), ref("b")]),
            )
            self.assertEqual(ledger.records(), [])

    def test_residual_qualifiers_and_incomplete_scope(self):
        item = evidence("b", "2")
        item["attributes"]["scope"]["value"]["qualifiers"] = ["excludes discontinued operations"]
        ledger = CalculationLedger(snapshot(evidence("a", "10"), item))
        self.assert_error(
            "incompatible_scope", lambda: calc(ledger, "ratio", [ref("a"), ref("b")], FRACTION)
        )
        item["attributes"]["scope"]["value"]["complete"] = False
        self.assert_error("incomplete_scope", lambda: CalculationLedger(snapshot(item)))

    def test_mixed_rate_representations_ratio_growth_and_add(self):
        ledger = CalculationLedger(
            snapshot(
                evidence("a", "0.5", metric="rate", role="rate", units=FRACTION),
                evidence("b", "25", metric="rate", role="rate", units=PERCENT),
            )
        )
        ratio = calc(ledger, "ratio", [ref("a"), ref("b")], FRACTION)
        self.assertEqual(ratio["numeric"]["display_value"], "2.00")
        growth = calc(ledger, "relative_growth_percent", [ref("a"), ref("b")], PERCENT)
        self.assertEqual(growth["numeric"]["display_value"], "100.00")
        self.assertEqual(growth["result_metadata"]["period"]["kind"], "comparison")
        self.assertEqual(
            calc(ledger, "add", [ref("a"), ref("b")], PERCENT)["numeric"]["display_value"], "75.00"
        )

    def test_chains_use_precision_result_not_display(self):
        ledger = CalculationLedger(
            snapshot(
                evidence("a", "1"),
                evidence("b", "3"),
                evidence("half", "0.5", metric="half", role="rate", units=FRACTION),
            )
        )
        first = calc(ledger, "ratio", [ref("a"), ref("b")], FRACTION, places=0)
        self.assertEqual(first["numeric"]["display_value"], "0")
        second = calc(
            ledger,
            "ratio",
            [ref(first["calculation_id"], "calculation"), ref("half")],
            FRACTION,
            places=4,
        )
        self.assertEqual(second["numeric"]["display_value"], "0.6667")
        self.assertEqual(second["depth"], 2)

    def test_duration_and_instant_rules(self):
        for period in (
            {"kind": "duration", "start": "2023-01-01", "end": "2023-04-01"},
            {"kind": "duration", "start": "2022-01-01", "end": "2023-01-07"},
            {"kind": "instant", "date": "2023-12-31"},
        ):
            item = evidence("b", "10")
            attr(item, "period", period)
            ledger = CalculationLedger(snapshot(evidence("a", "20"), item))
            self.assert_error(
                "incompatible_periods",
                lambda ledger=ledger: calc(
                    ledger, "relative_growth_percent", [ref("a"), ref("b")], PERCENT
                ),
            )
        first, second = evidence("a", "20"), evidence("b", "10")
        attr(first, "period", {"kind": "instant", "date": "2024-12-31"})
        attr(second, "period", {"kind": "instant", "date": "2023-12-31"})
        ledger = CalculationLedger(snapshot(first, second))
        result = calc(ledger, "subtract", [ref("a"), ref("b")])
        self.assertEqual(result["checks"]["period_rule"], "instant_comparison")
        self.assert_error(
            "incompatible_periods", lambda: calc(ledger, "ratio", [ref("a"), ref("b")], FRACTION)
        )

    def test_output_unit_roles_and_duplicate_operands(self):
        ledger = CalculationLedger(snapshot(evidence("a", "10"), evidence("b", "2")))
        self.assert_error(
            "output_unit_mismatch", lambda: calc(ledger, "ratio", [ref("a"), ref("b")], PERCENT)
        )
        self.assert_error(
            "invalid_margin_roles",
            lambda: calc(ledger, "margin_percent", [ref("a"), ref("b")], PERCENT),
        )
        self.assert_error("duplicate_operand", lambda: calc(ledger, "add", [ref("a")] * 2))
        self.assertEqual(ledger.records(), [])

    def test_snapshot_and_returned_results_are_copied(self):
        original = snapshot(evidence("a", "10"), evidence("b", "2"))
        ledger = CalculationLedger(original)
        attr(original["evidence"][0], "value", "999")
        result = calc(ledger, "ratio", [ref("a"), ref("b")], FRACTION)
        expected = copy.deepcopy(result)
        result["numeric"]["precision_result"] = "999"
        ledger.records()[0]["result_metadata"]["scope"]["identity"] = "forged"
        self.assertEqual(calc(ledger, "ratio", [ref("a"), ref("b")], FRACTION), expected)
        self.assertEqual(len(ledger.records()), 1)

    def test_admission_is_not_an_accepted_flag_and_support_is_required(self):
        for change, code in (
            (lambda e: e.update(accepted=True), "invalid_record_fields"),
            (lambda e: e.update(delivery="partial"), "ineligible_evidence"),
            (lambda e: e.update(quarantined=True), "ineligible_evidence"),
            (lambda e: e.update(kind="search_hit"), "invalid_evidence_kind"),
            (lambda e: e.update(run_id="other"), "cross_run_evidence"),
            (
                lambda e: e["attributes"]["value"].update(support_refs=["absent"]),
                "unknown_support_reference",
            ),
            (lambda e: e["attributes"]["value"].update(value=None), "nil_operand"),
        ):
            item = evidence("a", "1")
            change(item)
            self.assert_error(code, lambda item=item: CalculationLedger(snapshot(item)))
        self.assert_error(
            "duplicate_evidence_id",
            lambda: CalculationLedger(snapshot(evidence("a", "1"), evidence("a", "2"))),
        )

    def test_unknown_future_and_cross_run_references(self):
        ledger = CalculationLedger(snapshot(evidence("a", "10"), evidence("b", "2")))
        self.assert_error("invalid_record_fields", lambda: calc(ledger, "add", [1, 2]))
        self.assert_error(
            "unknown_evidence_reference",
            lambda: calc(ledger, "ratio", [ref("a"), ref("missing")], FRACTION),
        )
        self.assert_error(
            "unknown_calculation_reference",
            lambda: calc(ledger, "ratio", [ref("a"), ref("future", "calculation")], FRACTION),
        )
        other_snapshot = snapshot(evidence("a", "10"), evidence("b", "2"))
        other_snapshot["run_id"] = "other"
        for item in other_snapshot["evidence"]:
            item["run_id"] = "other"
        other = CalculationLedger(other_snapshot)
        foreign = calc(other, "ratio", [ref("a"), ref("b")], FRACTION)
        self.assert_error(
            "unknown_calculation_reference",
            lambda: calc(
                ledger, "ratio", [ref(foreign["calculation_id"], "calculation")] * 2, FRACTION
            ),
        )

    def test_depth_limit_and_atomic_failure(self):
        ledger = CalculationLedger(snapshot(evidence("a", "1", units=FRACTION)))
        current = ref("a")
        for depth in range(1, 17):
            result = calc(ledger, "ratio", [current, ref("a")], FRACTION)
            self.assertEqual(result["depth"], depth)
            current = ref(result["calculation_id"], "calculation")
        before = ledger.records()
        self.assert_error(
            "calculation_depth_limit", lambda: calc(ledger, "ratio", [current, ref("a")], FRACTION)
        )
        self.assertEqual(ledger.records(), before)
        large = evidence("x" * 7000, "1")
        ledger = CalculationLedger(snapshot(large, evidence("b", "2")))
        self.assert_error(
            "response_size_limit",
            lambda: calc(ledger, "ratio", [ref(large["evidence_id"]), ref("b")], FRACTION),
        )
        self.assertEqual(ledger.records(), [])

    def test_replay_rejects_record_and_admission_tampering(self):
        trusted = snapshot(evidence("a", "10"), evidence("b", "2"))
        ledger = CalculationLedger(trusted)
        calc(ledger, "ratio", [ref("a"), ref("b")], FRACTION)
        for field in ("depth", "operand_hashes", "checks", "result_metadata", "numeric"):
            records = ledger.records()
            records[0][field] = None
            self.assert_error(
                "calculation_replay_mismatch",
                lambda records=records: replay_calculations(trusted, records),
            )
        changed = copy.deepcopy(trusted)
        changed["evidence"][0]["source"]["original_sha256"] = "c" * 64
        self.assert_error(
            "calculation_replay_mismatch", lambda: replay_calculations(changed, ledger.records())
        )
        records = ledger.records()
        records[0]["request"]["operand_refs"].reverse()
        self.assert_error(
            "calculation_replay_mismatch", lambda: replay_calculations(trusted, records)
        )
        self.assert_error(
            "duplicate_calculation_record",
            lambda: replay_calculations(trusted, ledger.records() * 2),
        )

    def test_replay_preserves_order_and_distinct_evidence_occurrences(self):
        trusted = snapshot(evidence("a", "1e34"), evidence("b", "1"), evidence("c", "-1e34"))
        ledger = CalculationLedger(trusted)
        result = calc(ledger, "add", [ref("a"), ref("b"), ref("c")])
        self.assertEqual(result["numeric"]["precision_result"], "0E+1")
        reordered = calc(ledger, "add", [ref("a"), ref("c"), ref("b")])
        self.assertEqual(reordered["numeric"]["precision_result"], "1")
        changed = copy.deepcopy(result)
        changed["request"]["operand_refs"] = reordered["request"]["operand_refs"]
        self.assert_error(
            "calculation_replay_mismatch", lambda: replay_calculations(trusted, [changed])
        )
        ledger = CalculationLedger(snapshot(evidence("first", "10"), evidence("second", "10")))
        result = calc(ledger, "add", [ref("first"), ref("second")])
        self.assertEqual(result["evidence_ids"], ["first", "second"])
        self.assertNotEqual(*result["operand_hashes"])
