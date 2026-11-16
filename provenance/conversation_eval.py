"""Conversation answer-only metrics with fixed turn and conversation denominators."""


def score_conversation(task, prediction):
    from provenance.benchmarks import score_answer

    expected = task["reference"]["turns"]
    invalid = {
        "status": "invalid_output",
        "passed": False,
        "turn_count": len(expected),
        "turn_passed_count": 0,
        "turn_accuracy": 0.0,
        "turns": [],
    }
    if (
        not isinstance(prediction, dict)
        or set(prediction) != {"turns"}
        or not isinstance(prediction["turns"], list)
    ):
        return invalid
    by_index = {}
    for row in prediction["turns"]:
        if not isinstance(row, dict) or type(row.get("turn_index")) is not int:
            return invalid
        index = row["turn_index"]
        if not 0 <= index < len(expected) or index in by_index:
            raise ValueError("Duplicate or out-of-range conversation turn")
        by_index[index] = row
    rows = []
    for index, target in enumerate(expected):
        row = by_index.get(index)
        if row is None or row.get("status") != "completed":
            rows.append({"turn_index": index, "passed": False, "status": "missing_or_incomplete"})
            continue
        synthetic = {
            "id": f"{task['id']}_{index}",
            "dataset": "finqa",
            "reference": {"metric": "convfinqa_answer_only_adapted", "exe_ans": target["exe_ans"]},
        }
        result = score_answer(synthetic, row.get("output"))
        rows.append({"turn_index": index, **result})
    passed = sum(row["passed"] is True for row in rows)
    return {
        "status": "scored",
        "passed": passed == len(expected),
        "turn_count": len(expected),
        "turn_passed_count": passed,
        "turn_accuracy": passed / len(expected),
        "turns": rows,
    }
