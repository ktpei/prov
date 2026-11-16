"""Synthetic arithmetic fixtures; no source admission or financial accuracy claim."""

import copy
import unittest
from decimal import Decimal, DefaultContext, Inexact, localcontext

from provenance.calculation_numeric import (
    CalculationError,
    checked_response,
    decimal_input,
    evaluate_numeric,
)


def operand(value, scale=0, rate="none"):
    return {"value": value, "scale": scale, "rate_representation": rate}


def calculate(operation, values, places=2):
    return evaluate_numeric(operation, [operand(v) for v in values], {"decimal_places": places})


class NumericCalculationTests(unittest.TestCase):
    def assert_error(self, code, callback):
        with self.assertRaises(CalculationError) as caught:
            callback()
        self.assertEqual(caught.exception.code, code)

    def test_no_prerounding_and_order_is_preserved(self):
        result = calculate(
            "add", ["12345678901234567890123456789012345", "-12345678901234567890123456789012344"]
        )
        self.assertEqual(result["precision_result"], "1")
        self.assertEqual(result["arithmetic_flags"], {"inexact": False, "rounded": False})
        result = calculate("add", ["1e34", "1", "-1e34"])
        self.assertEqual(result["precision_result"], "0E+1")
        self.assertEqual(result["arithmetic_flags"], {"inexact": True, "rounded": True})
        result = calculate("add", ["1e34", "-1e34", "1"])
        self.assertEqual(result["precision_result"], "1")
        self.assertEqual(result["arithmetic_flags"], {"inexact": False, "rounded": False})

    def test_formulas_and_independent_rounding_flags(self):
        for operation, values, expected in (
            ("subtract", ["120", "100"], "20"),
            ("ratio", ["1", "3"], "0.3333333333333333333333333333333333"),
            ("margin_percent", ["1", "3"], "33.33333333333333333333333333333333"),
            ("relative_growth_percent", ["4", "3"], "33.33333333333333333333333333333333"),
            ("relative_growth_percent", ["110", "100"], "1E+1"),
        ):
            with self.subTest(operation=operation):
                result = calculate(operation, values)
                self.assertEqual(result["precision_result"], expected)
        result = calculate("add", ["1.0000000000000000000000000000000000", "0"])
        self.assertEqual(result["arithmetic_flags"], {"inexact": False, "rounded": True})
        result = calculate("ratio", ["2.345", "1"])
        self.assertEqual(result["arithmetic_flags"], {"inexact": False, "rounded": False})
        self.assertEqual(result["display_flags"], {"inexact": True, "rounded": True})

    def test_exact_scale_and_rate_conversion(self):
        values = [operand("1.2", 6), operand("200", 3)]
        original = copy.deepcopy(values)
        result = evaluate_numeric("add", values, {"decimal_places": 0})
        self.assertEqual(Decimal(result["precision_result"]), Decimal("1400000"))
        self.assertEqual(values, original)
        self.assertEqual(result["operands"][0]["base_scaled_value"], "1.2E+6")
        result = evaluate_numeric(
            "percentage_point_difference",
            [operand("0.125", rate="fraction"), operand("10", rate="percent")],
            {"decimal_places": 1},
        )
        self.assertEqual(result["precision_result"], "2.5")
        long = "12345678901234567890123456789012345"
        result = evaluate_numeric(
            "ratio", [operand(long, 2), operand(long, 2)], {"decimal_places": 2}
        )
        self.assertEqual(result["precision_result"], "1")
        self.assertEqual(result["arithmetic_flags"], {"inexact": False, "rounded": False})

    def test_internal_percent_scaling_does_not_round_or_reject(self):
        for value in ("9e100", "12345678901234567890123456789012345"):
            result = calculate("margin_percent", [value, value])
            self.assertEqual(Decimal(result["precision_result"]), Decimal("100"))
            self.assertEqual(result["arithmetic_flags"], {"inexact": False, "rounded": False})

    def test_half_even_display_and_large_outputs(self):
        for value, expected in (("2.345", "2.34"), ("2.355", "2.36"), ("-2.345", "-2.34")):
            result = calculate("ratio", [value, "1"])
            self.assertEqual(result["display_value"], expected)
            self.assertEqual(result["precision_result"], value)
        result = calculate("ratio", ["1e100", "1"], places=12)
        self.assertEqual(result["display_value"], "1" + "0" * 100 + "." + "0" * 12)
        self.assertEqual(result["display_flags"], {"inexact": False, "rounded": False})

    def test_lexical_bounds_before_normalization(self):
        self.assertEqual(decimal_input("0" * 128), Decimal(0))
        for value in ("0" * 129, "1" + "0" * 128, "1." + "0" * 128):
            self.assert_error("coefficient_limit", lambda value=value: decimal_input(value))
        self.assertEqual(decimal_input("1e" + "0" * 300 + "1"), Decimal("10"))
        for value in ("1e101", "1e-101", "1.0e-100", "99e100", "1e" + "9" * 300):
            self.assert_error("exponent_limit", lambda value=value: decimal_input(value))
        self.assert_error("lexical_length_limit", lambda: decimal_input("1e" + "0" * 511))

    def test_rejects_non_decimal_input_and_nil(self):
        for value in (True, False, 1, 0.1, Decimal("1"), [], {}):
            self.assert_error("decimal_string_required", lambda value=value: decimal_input(value))
        for value in ("NaN", "Infinity", "-inf", " 1", "1 ", "1_000", "١", "1e", "1e+", "."):
            self.assert_error("invalid_decimal", lambda value=value: decimal_input(value))
        self.assert_error("nil_operand", lambda: decimal_input(None))

    def test_persisted_normalized_and_result_bounds(self):
        for operation, values in (("add", ["9e100", "9e100"]), ("ratio", ["1e-99", "3"])):
            self.assert_error(
                "exponent_limit",
                lambda operation=operation, values=values: calculate(operation, values),
            )
        for value in (operand("9e100", 1), operand("9e100", rate="fraction")):
            self.assert_error(
                "exponent_limit",
                lambda value=value: evaluate_numeric(
                    "add", [value, operand("1")], {"decimal_places": 2}
                ),
            )

    def test_zero_and_growth_baseline_errors(self):
        for operation in ("ratio", "margin_percent"):
            self.assert_error(
                "division_by_zero", lambda operation=operation: calculate(operation, ["1", "-0"])
            )
        for baseline in ("0", "-0", "-1"):
            self.assert_error(
                "unsupported_growth_baseline",
                lambda baseline=baseline: calculate("relative_growth_percent", ["1", baseline]),
            )

    def test_arity_rounding_and_scale_contracts(self):
        self.assertEqual(calculate("add", ["1"] * 32)["precision_result"], "32")
        for operation, count in (("add", 1), ("add", 33), ("ratio", 1), ("subtract", 3)):
            self.assert_error(
                "operand_count",
                lambda operation=operation, count=count: calculate(operation, ["1"] * count),
            )
        for rounding in (
            {},
            {"decimal_places": True},
            {"decimal_places": -1},
            {"decimal_places": 13},
            {"decimal_places": 2, "rounding": "HALF_UP"},
        ):
            self.assert_error(
                "invalid_rounding_policy",
                lambda rounding=rounding: evaluate_numeric(
                    "add", [operand("1"), operand("1")], rounding
                ),
            )
        for scale in (None, True, 1.0, -101, 101):
            self.assert_error(
                "invalid_scale",
                lambda scale=scale: evaluate_numeric(
                    "add", [operand("1", scale), operand("1")], {"decimal_places": 2}
                ),
            )
        self.assert_error(
            "rate_operands_required", lambda: calculate("percentage_point_difference", ["1", "2"])
        )

    def test_fresh_context_and_response_size_boundary(self):
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.traps[Inexact] = True
            self.assertEqual(calculate("ratio", ["1", "3"])["precision_result"], "0." + "3" * 34)
            self.assertEqual(ctx.prec, 2)
            self.assertFalse(ctx.flags[Inexact])
        self.assertEqual(checked_response("a" * 11998), "a" * 11998)
        self.assert_error("response_size_limit", lambda: checked_response("a" * 11999))
        values = [operand("1" + "0" * 99)] * 32
        self.assert_error(
            "response_size_limit",
            lambda: evaluate_numeric("add", values, {"decimal_places": 2}),
        )

    def test_default_flags_and_exponent_case_cannot_change_records(self):
        expected = calculate("ratio", ["1e34", "1"])
        old_flag = DefaultContext.flags[Inexact]
        try:
            DefaultContext.flags[Inexact] = True
            with localcontext() as ctx:
                ctx.capitals = 0
                self.assertEqual(calculate("ratio", ["1e34", "1"]), expected)
        finally:
            DefaultContext.flags[Inexact] = old_flag
