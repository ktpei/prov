"""Synthetic validation and leakage tests for table/conversation adapters."""

import copy
import math
import unittest

from provenance.table_conversation_adapters import (
    adapt_convfinqa,
    adapt_tatqa,
    conversation_input,
)


def tatqa_group(group_id="table-1", question_id="question-1"):
    return {
        "table": {"uid": group_id, "table": [["Item", "2024"], ["Revenue", "10"]]},
        "paragraphs": [{"uid": "paragraph-1", "order": 1, "text": "Synthetic report context."}],
        "questions": [
            {
                "uid": question_id,
                "order": 1,
                "question": "What was revenue?",
                "answer": ["10"],
                "derivation": "",
                "answer_type": "span",
                "answer_from": "table",
                "rel_paragraphs": [],
                "req_comparison": False,
                "scale": "million",
            }
        ],
    }


def conversation(conversation_id="conv-1"):
    sentinel = "GOLD_SENTINEL_DO_NOT_EXPOSE"
    return {
        "id": conversation_id,
        "filename": "synthetic-report.json",
        "pre_text": ["Permitted introduction."],
        "post_text": ["Permitted conclusion."],
        "table": [["Item", "2023", "2024"], ["Revenue", "8", "10"]],
        "table_ori": [[sentinel]],
        "qa": {"question": sentinel, "answer": sentinel},
        "qa_0": {"question": sentinel},
        "qa_1": {"question": sentinel},
        "annotation": {
            "dialogue_break": [
                "What was revenue in 2024?",
                "How much did it increase? FUTURE_QUESTION_SENTINEL",
                "Was the increase positive? FINAL_FUTURE_SENTINEL",
            ],
            "turn_program": [
                f"table_lookup(Revenue, 2024) {sentinel}",
                "subtract(10, 8) FUTURE_PROGRAM_SENTINEL",
                "greater(2, 0) FINAL_PROGRAM_SENTINEL",
            ],
            "exe_ans_list": [10.0, 2.0, "yes"],
            "qa_split": ["single", "multi", "multi"],
            "gold_inds": sentinel,
            "model_input": sentinel,
        },
    }


class TatqaAdapterTests(unittest.TestCase):
    def test_expands_questions_and_keeps_gold_private(self):
        record = tatqa_group()
        second = copy.deepcopy(record["questions"][0])
        second.update(
            uid="question-2",
            order=2,
            question="How many revenue values are shown?",
            answer=2,
            answer_type="count",
            scale="",
        )
        second["custom_annotation"] = {"source": "synthetic-gold"}
        record["questions"].append(second)

        rows = adapt_tatqa([record], source_split="dev")

        self.assertEqual([row["id"] for row in rows], ["question-1", "question-2"])
        self.assertEqual(
            set(rows[0]),
            {
                "id",
                "dataset",
                "subset",
                "source_split",
                "question",
                "context",
                "reference",
                "metadata",
            },
        )
        self.assertEqual(rows[0]["dataset"], "tatqa")
        self.assertEqual(rows[0]["subset"], "default")
        self.assertEqual(rows[0]["metadata"], {"doc_name": "table-1", "group_id": "table-1"})
        self.assertEqual(rows[1]["reference"]["answer"], 2)
        self.assertEqual(rows[1]["reference"]["custom_annotation"]["source"], "synthetic-gold")
        self.assertEqual(rows[0]["reference"]["metric"], "tatqa_official_em_f1")
        self.assertNotIn("answer", rows[0]["context"])
        self.assertIsNot(rows[0]["context"]["table"], rows[1]["context"]["table"])

    def test_empty_answer_member_is_preserved_and_flagged(self):
        record = tatqa_group()
        record["questions"][0]["answer"] = ["10", ""]

        row = adapt_tatqa([record], source_split="dev")[0]

        self.assertEqual(row["reference"]["answer"], ["10", ""])
        self.assertIn("requires_review", row["reference"])

    def test_rejects_duplicate_ids_bad_table_gold_type_and_order(self):
        duplicate_question = tatqa_group(question_id="same")
        duplicate_question["questions"].append(
            {**copy.deepcopy(duplicate_question["questions"][0]), "order": 2}
        )
        cases = [
            ([tatqa_group("same", "q1"), tatqa_group("same", "q2")], "Duplicate group ID"),
            ([duplicate_question], "Duplicate question ID"),
        ]
        for records, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                adapt_tatqa(records, source_split="dev")

        malformed = tatqa_group()
        malformed["table"]["table"][1].append("ragged")
        with self.assertRaisesRegex(ValueError, "rectangular"):
            adapt_tatqa([malformed], source_split="dev")
        malformed = tatqa_group()
        malformed["questions"][0]["answer"] = math.inf
        with self.assertRaisesRegex(ValueError, "finite"):
            adapt_tatqa([malformed], source_split="dev")
        malformed = tatqa_group()
        malformed["questions"][0]["answer_type"] = "unsupported"
        with self.assertRaisesRegex(ValueError, "unsupported answer_type"):
            adapt_tatqa([malformed], source_split="dev")
        malformed = tatqa_group()
        malformed["paragraphs"].append({"uid": "paragraph-2", "order": 0, "text": "Out of order."})
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            adapt_tatqa([malformed], source_split="dev")


class ConvFinqaAdapterTests(unittest.TestCase):
    def test_normalizes_conversation_and_isolates_gold_sentinels(self):
        record = conversation()

        row = adapt_convfinqa([record], source_split="dev")[0]

        self.assertEqual(row["question"], record["annotation"]["dialogue_break"][0])
        self.assertEqual(
            row["context"],
            {
                "pre_text": record["pre_text"],
                "post_text": record["post_text"],
                "table": record["table"],
            },
        )
        self.assertNotIn("GOLD_SENTINEL_DO_NOT_EXPOSE", str(row["context"]))
        self.assertEqual(row["metadata"]["conversation_id"], record["id"])
        self.assertEqual(row["reference"]["turns"][0]["exe_ans"], 10.0)
        self.assertEqual(row["reference"]["turns"][2]["exe_ans"], "yes")
        self.assertEqual(row["reference"]["qa_split"], ["single", "multi", "multi"])

    def test_preserves_zero_yes_no_and_rejects_bad_results(self):
        record = conversation()
        record["annotation"]["exe_ans_list"] = [0, "yes", "no"]
        row = adapt_convfinqa([record], source_split="dev")[0]
        self.assertIs(type(row["reference"]["turns"][0]["exe_ans"]), int)
        self.assertEqual([turn["exe_ans"] for turn in row["reference"]["turns"]], [0, "yes", "no"])
        for bad in (True, None, math.nan, math.inf, "0"):
            with self.subTest(bad=bad):
                malformed = conversation()
                malformed["annotation"]["exe_ans_list"][0] = bad
                with self.assertRaisesRegex(ValueError, "finite numeric or yes/no"):
                    adapt_convfinqa([malformed], source_split="dev")

    def test_rejects_duplicate_alignment_and_rectangular_failures(self):
        with self.assertRaisesRegex(ValueError, "Duplicate conversation ID"):
            adapt_convfinqa([conversation(), conversation()], source_split="dev")
        malformed = conversation()
        malformed["annotation"]["turn_program"].pop()
        with self.assertRaisesRegex(ValueError, "aligned non-empty lengths"):
            adapt_convfinqa([malformed], source_split="dev")
        malformed = conversation()
        malformed["annotation"]["qa_split"].pop()
        with self.assertRaisesRegex(ValueError, "qa_split must align"):
            adapt_convfinqa([malformed], source_split="dev")
        malformed = conversation()
        malformed["table"][1].pop()
        with self.assertRaisesRegex(ValueError, "rectangular"):
            adapt_convfinqa([malformed], source_split="dev")


class ConversationInputTests(unittest.TestCase):
    def setUp(self):
        self.task = adapt_convfinqa([conversation()], source_split="dev")[0]

    def test_reference_history_has_only_prior_oracle_answers(self):
        payload = conversation_input(self.task, 1, condition="reference_history")

        self.assertEqual(payload["id"], "conv-1_1")
        self.assertEqual(payload["question"], "How much did it increase? FUTURE_QUESTION_SENTINEL")
        self.assertEqual(
            payload["history"], [{"question": "What was revenue in 2024?", "answer": 10.0}]
        )
        self.assertNotIn("FINAL_FUTURE_SENTINEL", str(payload))
        self.assertNotIn("PROGRAM_SENTINEL", str(payload))
        self.assertNotIn("2.0", str(payload["history"]))

    def test_agent_history_retains_wrong_answer_without_gold_fallback(self):
        payload = conversation_input(self.task, 1, condition="agent_history", history=[999])

        self.assertEqual(payload["history"][0]["answer"], 999)
        self.assertNotEqual(payload["history"][0]["answer"], 10.0)
        self.assertEqual(payload["condition"], "agent_history")

    def test_history_conditions_and_indices_are_strict(self):
        with self.assertRaisesRegex(ValueError, "history=None"):
            conversation_input(self.task, 1, condition="reference_history", history=[10])
        for history in (None, [], [1, 2]):
            with (
                self.subTest(history=history),
                self.assertRaisesRegex(ValueError, "exactly turn_index"),
            ):
                conversation_input(self.task, 1, condition="agent_history", history=history)
        for bad in (True, -1, 3, 1.0):
            with self.subTest(turn_index=bad), self.assertRaises(ValueError):
                conversation_input(self.task, bad, condition="reference_history")
        for bad in (True, None, math.nan, math.inf, [1], {"answer": 1}):
            with self.subTest(answer=bad), self.assertRaises(ValueError):
                conversation_input(self.task, 1, condition="agent_history", history=[bad])


if __name__ == "__main__":
    unittest.main()
