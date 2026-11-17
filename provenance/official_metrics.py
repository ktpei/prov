"""Bounded wrappers around pinned official metrics; no programs or remote code run."""

import math
import re
from decimal import Decimal

TATQA_SCALES = {"", "thousand", "million", "billion", "percent"}
TATQA_SCORER = "tatqa-870accc41953dcde885aabeb963d94aabdc0fbc3-wrapper-v2"


def load_tatqa_metric():
    """Check optional dependencies before any live TAT-QA request."""
    try:
        from provenance._vendor.tatqa.tatqa_metric import TaTQAEmAndF1
    except ImportError as exc:
        raise ValueError(
            "TAT-QA metrics require uv run --extra benchmark-metrics python ..."
        ) from exc
    return TaTQAEmAndF1


def score_tatqa(reference, prediction):
    """Preserve upstream EM/F1 and scale behavior with a strict JSON output contract."""
    if reference.get("scale") not in TATQA_SCALES or reference.get("answer_type") not in {
        "span",
        "multi-span",
        "arithmetic",
        "count",
    }:
        raise ValueError("Unsupported TAT-QA reference type or scale")
    result = {
        "scorer": TATQA_SCORER,
        "status": "invalid_output",
        "exact_match": 0.0,
        "f1": 0.0,
        "scale_accuracy": 0.0,
    }
    if not isinstance(prediction, dict) or set(prediction) != {"answer", "scale"}:
        return result
    scale, answer = prediction["scale"], prediction["answer"]
    if not isinstance(scale, str) or scale not in TATQA_SCALES:
        return result
    if type(answer) in (int, float):
        if not math.isfinite(answer):
            return result
        answer = format(Decimal(str(answer)), "f")  # Preserve zero and avoid exponent misparsing.
    if isinstance(answer, str):
        if not answer.strip() or len(answer) > 32_000:
            return result
    elif isinstance(answer, list):
        if not answer or len(answer) > 100 or any(not isinstance(item, str) for item in answer):
            return result
        if not any(item.strip() for item in answer):
            return result
        if sum(len(item) for item in answer) > 32_000:
            return result
    else:
        return result
    scientific = re.compile(
        r"(?<![A-Za-z0-9])[+-]?(?:\d+(?:\.\d*)?|\.\d+)[eE][+-]?\d+(?![A-Za-z0-9])"
    )
    if any(scientific.search(item) for item in ([answer] if isinstance(answer, str) else answer)):
        return result
    TaTQAEmAndF1 = load_tatqa_metric()
    metric = TaTQAEmAndF1()
    try:
        metric(ground_truth=reference, prediction=answer, pred_scale=scale)
    except (OverflowError, ValueError):
        return result
    em, f1, scale_accuracy, _ = metric.get_overall_metric()
    if not all(math.isfinite(value) for value in (em, f1, scale_accuracy)):
        return result
    return {
        "scorer": TATQA_SCORER,
        "status": "scored",
        "exact_match": float(em),
        "f1": float(f1),
        "scale_accuracy": float(scale_accuracy),
    }
