"""Pure adapters for table QA and conversational finance benchmarks."""

from __future__ import annotations

import copy
import math
from collections.abc import Iterable

_TASK_KEYS = {
    "id",
    "dataset",
    "subset",
    "source_split",
    "question",
    "context",
    "reference",
    "metadata",
}
_TATQA_ANSWER_TYPES = {"span", "multi-span", "arithmetic", "count"}
_CONVERSATION_CONDITIONS = {"reference_history", "agent_history"}


def _error(dataset, index, message):
    raise ValueError(f"Malformed {dataset} record {index}: {message}")


def _records(dataset, records, source_split):
    if not isinstance(source_split, str) or not source_split.strip():
        raise ValueError("source_split must be a non-empty string")
    if isinstance(records, (str, bytes, dict)):
        raise ValueError(f"records must be a non-empty iterable of {dataset} objects")
    try:
        records = list(records)
    except TypeError as exc:
        raise ValueError(f"records must be a non-empty iterable of {dataset} objects") from exc
    if not records:
        raise ValueError(f"Cannot adapt empty {dataset} dataset")
    return records


def _mapping(value, dataset, index, label):
    if not isinstance(value, dict):
        _error(dataset, index, f"{label} must be a JSON object")
    return value


def _text(value, dataset, index, label):
    if not isinstance(value, str) or not value.strip():
        _error(dataset, index, f"{label} must be a non-empty string")
    return value


def _matrix(value, dataset, index, label):
    if not isinstance(value, list) or not value:
        _error(dataset, index, f"{label} must be a non-empty rectangular string matrix")
    width = None
    for row in value:
        if not isinstance(row, list) or not row:
            _error(dataset, index, f"{label} must be a non-empty rectangular string matrix")
        if any(not isinstance(cell, str) for cell in row):
            _error(dataset, index, f"{label} must contain only strings")
        if width is None:
            width = len(row)
        elif len(row) != width:
            _error(dataset, index, f"{label} must be rectangular")
    return copy.deepcopy(value)


def _ordered(value, dataset, index, label):
    if type(value) is not int or value < 0:
        _error(dataset, index, f"{label} must be a non-negative integer")
    return value


def _gold_answer(value, index):
    if isinstance(value, list):
        if not value or any(not isinstance(item, str) for item in value):
            _error("tatqa", index, "question answer list must be a non-empty list of strings")
        return copy.deepcopy(value), any(item == "" for item in value)
    if isinstance(value, str):
        return value, False
    if type(value) in (int, float) and math.isfinite(value):
        return value, False
    _error("tatqa", index, "question answer must be a string, finite number, or string list")


def _tatqa_group(record, index, source_split, seen_questions, seen_groups):
    record = _mapping(record, "tatqa", index, "record")
    table = _mapping(record.get("table"), "tatqa", index, "table")
    group_id = _text(table.get("uid"), "tatqa", index, "table.uid")
    if group_id in seen_groups:
        raise ValueError(f"Duplicate group ID in tatqa: {group_id!r}")
    seen_groups.add(group_id)
    matrix = _matrix(table.get("table"), "tatqa", index, "table.table")

    paragraphs = record.get("paragraphs")
    if not isinstance(paragraphs, list):
        _error("tatqa", index, "paragraphs must be a list")
    context_paragraphs = []
    paragraph_ids = set()
    previous_order = -1
    for paragraph_index, paragraph in enumerate(paragraphs):
        paragraph = _mapping(paragraph, "tatqa", index, f"paragraphs[{paragraph_index}]")
        uid = _text(paragraph.get("uid"), "tatqa", index, f"paragraphs[{paragraph_index}].uid")
        if uid in paragraph_ids:
            _error("tatqa", index, f"duplicate paragraph uid {uid!r}")
        paragraph_ids.add(uid)
        order = _ordered(
            paragraph.get("order"), "tatqa", index, f"paragraphs[{paragraph_index}].order"
        )
        if order <= previous_order:
            _error("tatqa", index, "paragraphs must be in strictly increasing order")
        previous_order = order
        text = _text(paragraph.get("text"), "tatqa", index, f"paragraphs[{paragraph_index}].text")
        context_paragraphs.append({"uid": uid, "order": order, "text": text})

    questions = record.get("questions")
    if not isinstance(questions, list) or not questions:
        _error("tatqa", index, "questions must be a non-empty list")
    tasks = []
    previous_order = -1
    for question_index, question in enumerate(questions):
        question = _mapping(question, "tatqa", index, f"questions[{question_index}]")
        uid = _text(question.get("uid"), "tatqa", index, f"questions[{question_index}].uid")
        if uid in seen_questions:
            raise ValueError(f"Duplicate question ID in tatqa: {uid!r}")
        seen_questions.add(uid)
        order = _ordered(
            question.get("order"), "tatqa", index, f"questions[{question_index}].order"
        )
        if order <= previous_order:
            _error("tatqa", index, "questions must be in strictly increasing order")
        previous_order = order
        prompt = _text(
            question.get("question"), "tatqa", index, f"questions[{question_index}].question"
        )
        answer, requires_review = _gold_answer(question.get("answer"), index)
        answer_type = question.get("answer_type")
        if answer_type not in _TATQA_ANSWER_TYPES:
            _error("tatqa", index, f"unsupported answer_type {answer_type!r}")
        if answer_type in {"span", "multi-span"} and not isinstance(answer, list):
            _error("tatqa", index, "span answer must be a list")
        if answer_type == "arithmetic" and type(answer) not in (int, float):
            _error("tatqa", index, "arithmetic answer must be numeric")
        if answer_type == "count" and (isinstance(answer, list) or not str(answer).isdigit()):
            _error("tatqa", index, "count answer must be a nonnegative integer")
        if question.get("scale") not in {"", "thousand", "million", "billion", "percent"}:
            _error("tatqa", index, "unsupported answer scale")
        for key in ("scale", "derivation", "answer_from"):
            if not isinstance(question.get(key), str):
                _error("tatqa", index, f"questions[{question_index}].{key} must be a string")
        rel_paragraphs = question.get("rel_paragraphs")
        if not isinstance(rel_paragraphs, list) or any(
            not isinstance(item, str) for item in rel_paragraphs
        ):
            _error(
                "tatqa", index, f"questions[{question_index}].rel_paragraphs must be a string list"
            )
        if not isinstance(question.get("req_comparison"), bool):
            _error("tatqa", index, f"questions[{question_index}].req_comparison must be boolean")

        reference = {
            key: copy.deepcopy(value)
            for key, value in question.items()
            if key not in {"uid", "order", "question"}
        }
        reference["answer"] = answer
        reference["metric"] = "tatqa_official_em_f1"
        if requires_review:
            reference["requires_review"] = "Answer list contains an empty member"
        task = {
            "id": uid,
            "dataset": "tatqa",
            "subset": "default",
            "source_split": source_split,
            "question": prompt,
            "context": {
                "table": copy.deepcopy(matrix),
                "paragraphs": copy.deepcopy(context_paragraphs),
            },
            "reference": reference,
            "metadata": {"doc_name": group_id, "group_id": group_id},
        }
        assert set(task) == _TASK_KEYS
        tasks.append(task)
    return tasks


def adapt_tatqa(records: Iterable[dict], *, source_split) -> list[dict]:
    """Expand TAT-QA context groups into one private-reference task per question."""
    records = _records("tatqa", records, source_split)
    tasks = []
    seen_questions = set()
    seen_groups = set()
    for index, record in enumerate(records):
        tasks.extend(_tatqa_group(record, index, source_split, seen_questions, seen_groups))
    return tasks


def _conversation_result(value, index, turn_index):
    if type(value) in (int, float) and math.isfinite(value):
        return value
    if value in ("yes", "no"):
        return value
    _error(
        "convfinqa",
        index,
        f"annotation.exe_ans_list[{turn_index}] must be finite numeric or yes/no",
    )


def adapt_convfinqa(records: Iterable[dict], *, source_split) -> list[dict]:
    """Normalize ConvFinQA without copying evaluator-only helpers into context."""
    records = _records("convfinqa", records, source_split)
    tasks = []
    seen_ids = set()
    for index, record in enumerate(records):
        record = _mapping(record, "convfinqa", index, "record")
        conversation_id = _text(record.get("id"), "convfinqa", index, "id")
        if conversation_id in seen_ids:
            raise ValueError(f"Duplicate conversation ID in convfinqa: {conversation_id!r}")
        seen_ids.add(conversation_id)
        filename = _text(record.get("filename"), "convfinqa", index, "filename")
        context = {}
        for key in ("pre_text", "post_text"):
            value = record.get(key)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                _error("convfinqa", index, f"{key} must be a list of strings")
            context[key] = copy.deepcopy(value)
        context["table"] = _matrix(record.get("table"), "convfinqa", index, "table")

        annotation = _mapping(record.get("annotation"), "convfinqa", index, "annotation")
        questions = annotation.get("dialogue_break")
        programs = annotation.get("turn_program")
        results = annotation.get("exe_ans_list")
        if not all(isinstance(value, list) for value in (questions, programs, results)):
            _error(
                "convfinqa",
                index,
                "dialogue_break, turn_program, and exe_ans_list must be lists",
            )
        if not questions or len(questions) != len(programs) or len(questions) != len(results):
            _error(
                "convfinqa",
                index,
                "dialogue_break, turn_program, and exe_ans_list must have aligned non-empty lengths",
            )
        if any(not isinstance(value, str) or not value.strip() for value in questions):
            _error("convfinqa", index, "dialogue_break must contain non-empty strings")
        if any(not isinstance(value, str) or not value.strip() for value in programs):
            _error("convfinqa", index, "turn_program must contain non-empty strings")

        turns = [
            {
                "question": question,
                "program": program,
                "exe_ans": _conversation_result(result, index, turn_index),
            }
            for turn_index, (question, program, result) in enumerate(
                zip(questions, programs, results, strict=True)
            )
        ]
        reference = {"metric": "convfinqa_answer_only_adapted", "turns": turns}
        if "qa_split" in annotation:
            qa_split = annotation["qa_split"]
            if not isinstance(qa_split, list) or len(qa_split) != len(turns):
                _error("convfinqa", index, "annotation.qa_split must align with conversation turns")
            reference["qa_split"] = copy.deepcopy(qa_split)
        task = {
            "id": conversation_id,
            "dataset": "convfinqa",
            "subset": "default",
            "source_split": source_split,
            "question": questions[0],
            "context": context,
            "reference": reference,
            "metadata": {"filename": filename, "conversation_id": conversation_id},
        }
        assert set(task) == _TASK_KEYS
        tasks.append(task)
    return tasks


def _agent_answer(value, index):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"history[{index}] must be a non-boolean JSON scalar or string")
    if type(value) in (int, float):
        if not math.isfinite(value):
            raise ValueError(f"history[{index}] must be finite")
        return copy.deepcopy(value)
    if isinstance(value, str):
        return value
    raise ValueError(f"history[{index}] must be a JSON number or string")


def conversation_input(task, turn_index, *, condition, history=None):
    """Project one ConvFinQA turn without exposing future turns or gold programs."""
    if condition not in _CONVERSATION_CONDITIONS:
        raise ValueError(f"Unsupported conversation condition {condition!r}")
    if type(turn_index) is not int:
        raise ValueError("turn_index must be a non-boolean integer")
    if not isinstance(task, dict) or task.get("dataset") != "convfinqa":
        raise ValueError("task must be a normalized convfinqa task")
    metadata = task.get("metadata")
    reference = task.get("reference")
    context = task.get("context")
    if (
        not isinstance(metadata, dict)
        or not isinstance(reference, dict)
        or not isinstance(context, dict)
    ):
        raise ValueError("task must contain normalized metadata, reference, and context")
    conversation_id = metadata.get("conversation_id")
    if (
        not isinstance(conversation_id, str)
        or not conversation_id
        or task.get("id") != conversation_id
    ):
        raise ValueError("task conversation identity is invalid")
    turns = reference.get("turns")
    if not isinstance(turns, list) or turn_index < 0 or turn_index >= len(turns):
        raise ValueError("turn_index is outside the conversation")
    if condition == "reference_history":
        if history is not None:
            raise ValueError("reference_history requires history=None")
        answers = [turns[index].get("exe_ans") for index in range(turn_index)]
    else:
        if not isinstance(history, list) or len(history) != turn_index:
            raise ValueError("agent_history requires exactly turn_index prior answers")
        answers = [_agent_answer(value, index) for index, value in enumerate(history)]

    permitted_context = {}
    for key in ("pre_text", "post_text", "table"):
        if key not in context:
            raise ValueError(f"task context is missing {key!r}")
        permitted_context[key] = copy.deepcopy(context[key])
    prior = []
    for index, answer in enumerate(answers):
        previous = turns[index]
        if not isinstance(previous, dict) or not isinstance(previous.get("question"), str):
            raise ValueError("task reference turns are malformed")
        prior.append({"question": previous["question"], "answer": copy.deepcopy(answer)})
    current = turns[turn_index]
    if not isinstance(current, dict) or not isinstance(current.get("question"), str):
        raise ValueError("task reference turns are malformed")
    return {
        "id": f"{conversation_id}_{turn_index}",
        "conversation_id": conversation_id,
        "turn_index": turn_index,
        "question": current["question"],
        "context": permitted_context,
        "history": prior,
        "condition": condition,
    }
