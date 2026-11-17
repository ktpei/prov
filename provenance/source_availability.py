"""Conservative temporal eligibility for one exact source artifact, not its facts."""

import re
from datetime import datetime

_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)"
)


def timestamp(value):
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value):
        raise ValueError("Availability timestamps require explicit RFC3339 seconds and timezone")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid availability timestamp") from exc


def availability(source, as_of):
    """Evaluate declared bounds; metadata authenticity remains an ingestion obligation."""
    record = source.get("availability")
    lower = upper = None
    if record is not None:
        if not isinstance(record, dict) or set(record) != {
            "original_sha256",
            "not_before",
            "observed_by",
            "basis",
        }:
            raise ValueError("Malformed source availability metadata")
        if not isinstance(record["basis"], str) or not record["basis"].strip():
            raise ValueError("Availability requires an evidence basis")
        if (
            not isinstance(record["original_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", record["original_sha256"])
            or record["original_sha256"] != source.get("original_sha256")
        ):
            raise ValueError("Availability evidence refers to different original bytes")
        lower = timestamp(record["not_before"]) if record["not_before"] is not None else None
        upper = timestamp(record["observed_by"]) if record["observed_by"] is not None else None
        if lower is not None and upper is not None and lower > upper:
            raise ValueError("Availability bounds are reversed")
    if as_of is None:
        state = "not_requested"
    else:
        cutoff = timestamp(as_of)
        if lower is not None and cutoff < lower:
            state = "not_yet_available"
        elif upper is not None and cutoff >= upper:
            state = "available"
        else:
            state = "unknown"
    return {
        "policy": "source-availability-bounds-v1",
        "state": state,
        "allowed": state in {"available", "not_requested"},
        "as_of": as_of,
        "evidence": record,
        "scope": "This exact source artifact; no claim about facts published elsewhere.",
    }
