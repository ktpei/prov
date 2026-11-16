"""Normalize external finance benchmarks without exposing evaluator-only gold."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Iterable

_SUPPORTED_SUBSETS = {
    "fineval": {"CFA-Easy", "CFA-Challenge"},
    "finqa": {"default"},
    "financebench": {"open_source"},
    "tatqa": {"default"},
    "convfinqa": {"default"},
}


def _record_error(dataset, index, message):
    raise ValueError(f"Malformed {dataset} record {index}: {message}")


def _required_mapping(record, key, dataset, index):
    value = record.get(key)
    if not isinstance(value, dict):
        _record_error(dataset, index, f"{key!r} must be a JSON object")
    return value


def _required_text(record, key, dataset, index):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        _record_error(dataset, index, f"{key!r} must be a non-empty string")
    return value


def _required_value(record, key, dataset, index):
    if key not in record or record[key] is None or record[key] == "":
        _record_error(dataset, index, f"missing gold field {key!r}")
    if isinstance(record[key], bool):
        _record_error(dataset, index, f"gold field {key!r} must not be boolean")
    return record[key]


def _stable_id(dataset, record, upstream_key, index):
    if upstream_key in record:
        value = record[upstream_key]
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            _record_error(dataset, index, f"{upstream_key!r} must be a string or integer")
        if isinstance(value, str) and not value:
            _record_error(dataset, index, f"{upstream_key!r} must not be empty")
        return str(value)
    try:
        encoded = json.dumps(
            record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    except (TypeError, ValueError) as exc:
        _record_error(dataset, index, f"record cannot be content-hashed: {exc}")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _fineval(record, subset, index):
    question = _required_text(record, "query", "fineval", index)
    answer = _required_text(record, "answer", "fineval", index).strip().upper()
    if len(answer) != 1 or not answer.isascii() or not answer.isalpha() or not answer.isupper():
        _record_error("fineval", index, "'answer' must be one uppercase ASCII choice letter")

    reference = {"answer": answer, "metric": "choice_accuracy"}
    if subset == "CFA-Easy":
        choices = record.get("choices")
        gold = record.get("gold")
        if (
            not isinstance(choices, list)
            or not choices
            or any(not isinstance(choice, str) for choice in choices)
        ):
            _record_error("fineval", index, "'choices' must be a non-empty list of strings")
        if isinstance(gold, bool) or not isinstance(gold, int):
            _record_error("fineval", index, "'gold' must be an integer choice index")
        if gold < 0 or gold >= len(choices):
            _record_error("fineval", index, "'gold', 'choices', and 'answer' are inconsistent")
        reference.update(gold=gold, choices=copy.deepcopy(choices))
        if choices[gold].strip().upper() != answer:
            reference["requires_review"] = "Upstream answer letter disagrees with gold choice index"
        if "text" in record:
            if not isinstance(record["text"], str):
                _record_error("fineval", index, "'text' must be a string when present")
            reference["explanation"] = record["text"]
    else:
        reference["source"] = _required_text(record, "source", "fineval", index)

    return question, {}, reference, {}


def _finqa(record, index):
    qa = _required_mapping(record, "qa", "finqa", index)
    question = _required_text(qa, "question", "finqa", index)
    context = {}
    for key in ("pre_text", "post_text"):
        value = record.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            _record_error("finqa", index, f"{key!r} must be a list of strings")
        context[key] = copy.deepcopy(value)
    table = record.get("table")
    if not isinstance(table, list) or any(
        not isinstance(row, list) or any(not isinstance(cell, str) for cell in row) for row in table
    ):
        _record_error("finqa", index, "'table' must be a list of string rows")
    context["table"] = copy.deepcopy(table)

    reference = {
        "answer": copy.deepcopy(qa.get("answer")),
        "exe_ans": copy.deepcopy(_required_value(qa, "exe_ans", "finqa", index)),
        "program": copy.deepcopy(_required_value(qa, "program", "finqa", index)),
        "metric": "finqa_answer_only_adapted",
    }
    value = reference["exe_ans"]
    if not (type(value) in (int, float) and math.isfinite(value)) and value not in ("yes", "no"):
        _record_error("finqa", index, "exe_ans must be finite numeric or yes/no")
    for key, value in qa.items():
        if key not in {"question", "answer", "exe_ans", "program", "metric"}:
            reference[key] = copy.deepcopy(value)
    for key in ("table_ori", "text_retrieved", "table_retrieved"):
        if key in record:
            reference[key] = copy.deepcopy(record[key])

    metadata = {}
    if "filename" in record:
        if not isinstance(record["filename"], str) or not record["filename"]:
            _record_error("finqa", index, "'filename' must be a non-empty string when present")
        metadata["filename"] = record["filename"]
    return question, context, reference, metadata


def _financebench(record, index):
    question = _required_text(record, "question", "financebench", index)
    reference = {
        "answer": copy.deepcopy(_required_value(record, "answer", "financebench", index)),
        "evidence": copy.deepcopy(_required_value(record, "evidence", "financebench", index)),
        "metric": "financebench_semantic_review",
    }
    if not isinstance(reference["evidence"], list) or not reference["evidence"]:
        _record_error("financebench", index, "evidence must be a nonempty list")
    for evidence in reference["evidence"]:
        if not isinstance(evidence, dict):
            _record_error("financebench", index, "evidence must contain objects")
        for key in ("doc_name", "evidence_text"):
            _required_text(evidence, key, "financebench", index)
        page = evidence.get("evidence_page_num")
        if type(page) is not int or page < 0:
            _record_error("financebench", index, "evidence_page_num must be a zero-based integer")
    _required_text(record, "doc_name", "financebench", index)
    if "justification" in record:
        reference["justification"] = copy.deepcopy(record["justification"])

    metadata = {}
    for key in ("doc_name", "company", "doc_period"):
        if key in record:
            metadata[key] = copy.deepcopy(record[key])
    return question, {}, reference, metadata


def adapt_records(dataset, records: Iterable[dict], *, subset, source_split) -> list[dict]:
    """Adapt upstream records while keeping gold data evaluator-only."""
    if dataset not in _SUPPORTED_SUBSETS:
        raise ValueError(f"Unsupported dataset {dataset!r}")
    if subset not in _SUPPORTED_SUBSETS[dataset]:
        supported = ", ".join(sorted(_SUPPORTED_SUBSETS[dataset]))
        raise ValueError(
            f"Unsupported subset {subset!r} for {dataset}; expected one of: {supported}"
        )
    if not isinstance(source_split, str) or not source_split:
        raise ValueError("source_split must be a non-empty string")
    if dataset in {"tatqa", "convfinqa"}:
        from provenance.table_conversation_adapters import adapt_convfinqa, adapt_tatqa

        adapter = adapt_tatqa if dataset == "tatqa" else adapt_convfinqa
        return adapter(records, source_split=source_split)
    if isinstance(records, (str, bytes, dict)):
        raise ValueError("records must be a non-empty iterable of JSON objects")
    try:
        records = list(records)
    except TypeError as exc:
        raise ValueError("records must be a non-empty iterable of JSON objects") from exc
    if not records:
        raise ValueError(f"Cannot adapt empty {dataset} dataset")

    adapted = []
    seen = set()
    id_key = {"fineval": "id", "finqa": "id", "financebench": "financebench_id"}[dataset]
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _record_error(dataset, index, "record must be a JSON object")
        stable_id = _stable_id(dataset, record, id_key, index)
        typed_id = (type(stable_id), stable_id)
        if typed_id in seen:
            raise ValueError(f"Duplicate stable ID in {dataset}: {stable_id!r}")
        seen.add(typed_id)

        if dataset == "fineval":
            question, context, reference, metadata = _fineval(record, subset, index)
        elif dataset == "finqa":
            question, context, reference, metadata = _finqa(record, index)
        else:
            question, context, reference, metadata = _financebench(record, index)
        adapted.append(
            {
                "id": stable_id,
                "dataset": dataset,
                "subset": subset,
                "source_split": source_split,
                "question": question,
                "context": context,
                "reference": reference,
                "metadata": metadata,
            }
        )
    return adapted
