"""Internal bounded arithmetic; this module does not admit evidence or expose a tool.

Financial compatibility, reference resolution, and controller budgets must be
enforced by the calculation ledger/dispatcher before model-facing integration.
"""

import json
import re
from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    localcontext,
)

POLICY = "bounded-decimal-v1"
OPERATIONS = {
    "add",
    "subtract",
    "ratio",
    "margin_percent",
    "relative_growth_percent",
    "percentage_point_difference",
}
LEXICAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE]([+-]?[0-9]+))?")


class CalculationError(ValueError):
    """A bounded, repairable arithmetic error; never a controller limit exception."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def bounded(value):
    """Check persisted-value limits without rounding or normalizing its coefficient."""
    if not value.is_finite():
        raise CalculationError("nonfinite_value")
    parts = value.as_tuple()
    if len(parts.digits) > 128:
        raise CalculationError("coefficient_limit")
    if not -100 <= parts.exponent <= 100 or not -100 <= value.adjusted() <= 100:
        raise CalculationError("exponent_limit")
    return value


def decimal_input(value):
    if value is None:
        raise CalculationError("nil_operand")
    if not isinstance(value, str):
        raise CalculationError("decimal_string_required")
    if len(value) > 512:
        raise CalculationError("lexical_length_limit")
    match = LEXICAL.fullmatch(value)
    if match is None:
        raise CalculationError("invalid_decimal")
    coefficient = re.split("[eE]", value)[0]
    if sum(character in "0123456789" for character in coefficient) > 128:
        raise CalculationError("coefficient_limit")
    exponent = match.group(1) or "0"
    unsigned = exponent.lstrip("+-").lstrip("0") or "0"
    if len(unsigned) > 3 or not -100 <= int(exponent) <= 100:
        raise CalculationError("exponent_limit")
    return bounded(Decimal(value))


def shift(value, exponent):
    """Exact power-of-ten scaling, including >34-digit source coefficients."""
    parts = value.as_tuple()
    return Decimal((parts.sign, parts.digits, parts.exponent + exponent))


def normalized_operand(operand):
    if not isinstance(operand, dict) or set(operand) != {
        "value",
        "scale",
        "rate_representation",
    }:
        raise CalculationError("invalid_numeric_operand")
    value = decimal_input(operand["value"])
    scale = operand["scale"]
    if type(scale) is not int or not -100 <= scale <= 100:
        raise CalculationError("invalid_scale")
    rate = operand["rate_representation"]
    if rate not in ("none", "fraction", "percent"):
        raise CalculationError("invalid_rate_representation")
    scaled = bounded(shift(value, scale))
    normalized = bounded(shift(scaled, 2)) if rate == "fraction" else scaled
    return normalized, {
        "value": operand["value"],
        "scale": scale,
        "rate_representation": rate,
        "base_scaled_value": str(scaled).upper(),
        "normalized_value": str(normalized).upper(),
        "rate_conversion_exponent": 2 if rate == "fraction" else 0,
    }


def flags(context):
    return {"inexact": context.flags[Inexact], "rounded": context.flags[Rounded]}


def arithmetic_context(precision):
    return Context(
        prec=precision,
        rounding=ROUND_HALF_EVEN,
        Emin=-1000,
        Emax=1000,
        capitals=1,
        clamp=0,
        flags=[],
        traps=[InvalidOperation, DivisionByZero, Overflow],
    )


def checked_response(record):
    """The full ledger must also apply this check after adding its provenance."""
    serialized = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(serialized) > 12_000:
        raise CalculationError("response_size_limit")
    return json.loads(serialized)


def evaluate_numeric(operation, operands, rounding_policy):
    """Pure numerical kernel, not an accepted evidence-linked calculation record."""
    if not isinstance(operation, str) or operation not in OPERATIONS:
        raise CalculationError("unsupported_operation")
    if not isinstance(operands, list):
        raise CalculationError("invalid_operands")
    if not (2 <= len(operands) <= 32 if operation == "add" else len(operands) == 2):
        raise CalculationError("operand_count")
    if not isinstance(rounding_policy, dict) or set(rounding_policy) != {"decimal_places"}:
        raise CalculationError("invalid_rounding_policy")
    places = rounding_policy["decimal_places"]
    if type(places) is not int or not 0 <= places <= 12:
        raise CalculationError("invalid_rounding_policy")
    values, transformations = [], []
    for operand in operands:
        value, transformation = normalized_operand(operand)
        values.append(value)
        transformations.append(transformation)
    if operation == "percentage_point_difference" and any(
        operand["rate_representation"] == "none" for operand in operands
    ):
        raise CalculationError("rate_operands_required")
    if operation in {"ratio", "margin_percent"} and values[1].is_zero():
        raise CalculationError("division_by_zero")
    if operation == "relative_growth_percent" and values[1] <= 0:
        raise CalculationError("unsupported_growth_baseline")
    try:
        with localcontext(arithmetic_context(34)) as ctx:
            if operation == "add":
                result = values[0]
                for value in values[1:]:
                    result = result + value
            elif operation in {"subtract", "percentage_point_difference"}:
                result = values[0] - values[1]
            elif operation == "ratio":
                result = values[0] / values[1]
            elif operation == "margin_percent":
                result = shift(values[0], 2) / values[1]
            else:
                result = shift(values[0] - values[1], 2) / values[1]
            bounded(result)
            arithmetic_flags = flags(ctx)
        with localcontext(arithmetic_context(128)) as ctx:
            display = bounded(result.quantize(Decimal((0, (1,), -places))))
            display_flags = flags(ctx)
    except DecimalException as exc:
        raise CalculationError("arithmetic_failure") from exc
    return checked_response(
        {
            "numeric_policy": POLICY,
            "operation": operation,
            "operands": transformations,
            "precision": 34,
            "rounding_mode": "ROUND_HALF_EVEN",
            "rounding_policy": {"decimal_places": places},
            "precision_result": str(result).upper(),
            "display_value": format(display, "f"),
            "arithmetic_flags": arithmetic_flags,
            "display_flags": display_flags,
            "validation": "Numerical arithmetic only; evidence and financial compatibility not checked",
        }
    )
