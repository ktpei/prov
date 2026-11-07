import copy
import json
import unittest

from provenance.context import project_messages, tool_result_chars
from provenance.controls import LimitReached


def pair(name, call_id, result):
    return [
        {"type": "function_call", "call_id": call_id, "name": name, "arguments": "{}"},
        {"type": "function_call_output", "call_id": call_id, "output": json.dumps(result)},
    ]


class ContextTests(unittest.TestCase):
    def test_projection_preserves_pairs_and_canonical_history(self):
        history = [{"role": "user", "content": "Research revenue"}]
        history += pair("search", "s1", {"results": [{"id": "old"}]})
        history += pair("search", "s2", {"results": [{"id": "new"}]})
        history += [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Investigating."}],
            }
        ]
        snapshot = copy.deepcopy(history)
        projected = project_messages(history)
        self.assertEqual(history, snapshot)
        self.assertEqual(projected[0], history[0])
        self.assertEqual(projected[-1], history[-1])
        self.assertEqual([m.get("call_id") for m in projected], [m.get("call_id") for m in history])
        self.assertEqual([m.get("type") for m in projected], [m.get("type") for m in history])
        self.assertTrue(json.loads(projected[2]["output"])["omitted_from_model_context"])
        self.assertEqual(projected[4], history[4])

    def test_exact_evidence_strings_unchanged_and_old_read_identified(self):
        evidence = {
            "id": "source",
            "locator": "L1-L2",
            "lines": [
                {"line": 1, "text": 'Revenue: $120 million; "unaudited".'},
                {"line": 2, "text": "Footnote: actuals, not guidance."},
            ],
        }
        history = pair("read_source", "r1", {**evidence, "padding": "x" * 1000})
        history += pair("search", "s1", {"results": [{"id": "source"}]})
        history += pair("read_source", "r2", evidence)
        projected = project_messages(history, max_tool_result_chars=700)
        self.assertEqual(projected[-1]["output"], history[-1]["output"])
        omitted = json.loads(projected[1]["output"])
        self.assertEqual(omitted["source_id"], "source")
        self.assertEqual(omitted["locator"], "L1-L2")
        self.assertLessEqual(tool_result_chars(projected), 700)

    def test_long_history_is_bounded_by_whole_result_omission(self):
        history = []
        for number in range(25):
            history += pair(
                "read_source",
                f"r{number}",
                {"id": str(number), "locator": "L1", "lines": [{"line": 1, "text": "x" * 2000}]},
            )
        projected = project_messages(history, max_tool_result_chars=8000)
        self.assertLessEqual(tool_result_chars(projected), 8000)
        self.assertEqual(projected[-1], history[-1])
        for old, new in zip(history, projected, strict=True):
            if old.get("type") == "function_call_output":
                self.assertTrue(
                    new == old or json.loads(new["output"])["omitted_from_model_context"]
                )

    def test_latest_oversized_result_stops_instead_of_clipping(self):
        history = pair("read_source", "r1", {"lines": [{"line": 1, "text": "x" * 1000}]})
        with self.assertRaisesRegex(LimitReached, "tool_context_size_limit"):
            project_messages(history, max_tool_result_chars=500)

    def test_latest_search_and_read_are_both_required(self):
        history = pair("search", "s1", {"results": [{"snippet": "x" * 500}]})
        history += pair("read_source", "r1", {"lines": [{"text": "y" * 500}]})
        with self.assertRaisesRegex(LimitReached, "tool_context_size_limit"):
            project_messages(history, max_tool_result_chars=900)
        self.assertEqual(project_messages(history, max_tool_result_chars=2000), history)

    def test_invalid_bounds_rejected(self):
        for value in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                project_messages([], max_tool_result_chars=value)
