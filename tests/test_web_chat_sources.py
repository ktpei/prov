import unittest
from pathlib import Path

from provenance.sources import TOOL_SCHEMAS
from provenance.web.chat_sources import (
    CHAT_INSTRUCTIONS,
    ChatSources,
    compose_question,
)
from provenance.web.workbook import load_snapshot

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data/cloudflare-2024-q3"
FIXTURE = ROOT / "data/demo/cloudflare-fy2024-model.xlsx"
RELEASE = "cloudflare-q3-2024-release"
GUIDANCE = {
    "source_id": RELEASE,
    "locator": "L63",
    "quote": "Total revenue of $1,661.0 to $1,662.0 million",
}


def snapshot():
    return load_snapshot(FIXTURE.read_bytes(), FIXTURE.name)


def sources(**kwargs):
    return ChatSources(CORPUS, **kwargs)


def edit(**overrides):
    return {
        "sheet": "Model",
        "cell": "B7",
        "new_content": 1661.5,
        "rationale": "Midpoint of the latest FY2024 revenue guidance",
        "citations": [GUIDANCE],
        **overrides,
    }


def propose(src, **overrides):
    """Propose one edit; return its single result (proposal or error)."""
    result = src.call("propose_cell_edits", {"edits": [edit(**overrides)]}, 5)
    return result["results"][0] if "results" in result else result


class ChatSourcesTests(unittest.TestCase):
    def test_schemas_only_with_workbook(self):
        self.assertEqual(sources().tool_schemas, TOOL_SCHEMAS)
        names = [schema["name"] for schema in sources(snapshot=snapshot()).tool_schemas]
        self.assertEqual(
            names, ["search", "read_source", "read_workbook_range", "propose_cell_edits"]
        )
        self.assertIn("propose_cell_edits", CHAT_INSTRUCTIONS)
        self.assertTrue(CHAT_INSTRUCTIONS.startswith("You are a read-only finance research agent"))

    def test_workbook_tools_unavailable_without_snapshot(self):
        result = sources().call("read_workbook_range", {"sheet": "Model", "range": "B7"}, 5)
        self.assertIn("error", result)

    def test_read_workbook_range_marks_seen(self):
        snap = snapshot()
        src = sources(snapshot=snap)
        result = src.call("read_workbook_range", {"sheet": "Model", "range": "A7:B7"}, 5)
        self.assertEqual(result["snapshot_id"], snap.snapshot_id)
        self.assertEqual(result["source_id"], f"workbook:{snap.snapshot_id}")
        self.assertEqual([cell["display"] for cell in result["cells"]][1], "1,650.0")
        self.assertIn("Model!B7", src.seen[f"workbook:{snap.snapshot_id}"])
        too_big = src.call("read_workbook_range", {"sheet": "Model", "range": "A1:Z20"}, 5)
        self.assertIn("error", too_big)
        bad_fields = src.call("read_workbook_range", {"sheet": "Model"}, 5)
        self.assertIn("error", bad_fields)

    def test_workbook_citation_rules(self):
        snap = snapshot()
        workbook_id = f"workbook:{snap.snapshot_id}"
        src = sources(snapshot=snap, preread_range=("Model", "B8:B8"))
        src.call("read_workbook_range", {"sheet": "Model", "range": "B7"}, 5)
        src.check_citation({"source_id": workbook_id, "locator": "Model!B7", "quote": "1650"})
        src.check_citation({"source_id": workbook_id, "locator": "Model!B7", "quote": "1,650.0"})
        with self.assertRaises(ValueError):
            src.check_citation({"source_id": workbook_id, "locator": "Model!B7", "quote": "1700"})
        src.check_citation({"source_id": workbook_id, "locator": "Model!B8", "quote": "215"})
        with self.assertRaises(ValueError):
            src.check_citation({"source_id": workbook_id, "locator": "Model!B9", "quote": "=B8/B7"})
        with self.assertRaises(ValueError):
            src.check_citation(
                {"source_id": "workbook:000000000000", "locator": "Model!B7", "quote": "1650"}
            )
        with self.assertRaises(ValueError):
            src.check_citation({"source_id": workbook_id, "locator": "B7", "quote": "1650"})

    def test_corpus_citation_unchanged(self):
        src = sources()
        read = src.call("read_source", {"source_id": RELEASE, "start_line": 59, "end_line": 64}, 5)
        self.assertNotIn("error", read)
        src.check_citation(GUIDANCE)
        with self.assertRaises(ValueError):
            src.check_citation({**GUIDANCE, "locator": "L70"})

    def test_propose_requires_read_evidence(self):
        src = sources(snapshot=snapshot())
        self.assertIn("error", propose(src))
        self.assertEqual(src.proposals, [])
        src.call("read_source", {"source_id": RELEASE, "start_line": 59, "end_line": 64}, 5)
        result = propose(src)
        self.assertEqual(result["proposal_id"], "P1")
        self.assertEqual(result["status"], "pending_human_approval")
        proposal = src.proposals[0]
        self.assertEqual(
            (proposal["sheet"], proposal["cell"], proposal["old_display"], proposal["old_formula"]),
            ("Model", "B7", "1,650.0", None),
        )
        self.assertEqual(proposal["new_content"], 1661.5)

    def test_propose_validation(self):
        src = sources(snapshot=snapshot())
        src.call("read_source", {"source_id": RELEASE, "start_line": 59, "end_line": 64}, 5)
        for overrides in (
            {"cell": "B0"},
            {"cell": "B7:B8"},
            {"sheet": "Missing"},
            {"rationale": "  "},
            {"new_content": "=" + "A" * 500},
            {"new_content": True},
            {"citations": []},
        ):
            self.assertIn("error", propose(src, **overrides), overrides)
        self.assertEqual(propose(src, new_content="1,661.5")["proposal_id"], "P1")
        self.assertEqual(src.proposals[0]["new_content"], 1661.5)
        self.assertEqual(propose(src, new_content=1662)["proposal_id"], "P1")
        self.assertEqual(len(src.proposals), 1)
        self.assertEqual(src.proposals[0]["new_content"], 1662)
        for row in range(10, 19):
            self.assertNotIn("error", propose(src, cell=f"B{row}"))
        self.assertEqual(len(src.proposals), 10)
        self.assertIn("error", propose(src, cell="B30"))


class ComposeQuestionTests(unittest.TestCase):
    def test_compose_question_with_context(self):
        snap = snapshot()
        history = [
            {
                "question": f"Question {index}",
                "status": "completed",
                "answer": {
                    "answerable": True,
                    "answer": f"Answer {index}",
                    "claims": [
                        {
                            "key": "fy2024_revenue_guidance_low",
                            "value": 1661.0,
                            "unit": "USD million",
                            "period": "FY2024",
                            "citations": [GUIDANCE],
                        }
                    ],
                },
            }
            for index in range(1, 5)
        ]
        text = compose_question(
            "Is B7 stale?",
            corpus_label="Cloudflare Q3 2024 packet",
            cutoff="2024-11-07",
            history=history,
            snapshot=snap,
            context={"sheet": "Model", "range": "B7:B7"},
        )
        self.assertIn("Evidence set: Cloudflare Q3 2024 packet", text)
        self.assertIn("2024-11-07", text)
        self.assertIn(f"workbook:{snap.snapshot_id}", text)
        self.assertIn("Model!B7 = 1,650.0", text)
        self.assertNotIn("Question 1", text)
        for index in (2, 3, 4):
            self.assertIn(f"Question {index}", text)
        self.assertIn(f"[{RELEASE} L63]", text)
        self.assertTrue(text.endswith("Current question: Is B7 stale?"))

    def test_compose_question_minimal(self):
        text = compose_question(
            "What was revenue?",
            corpus_label="Big Tech earnings excerpts",
            cutoff="2024-11-20",
            history=[],
            snapshot=None,
            context=None,
        )
        self.assertNotIn("Earlier in this conversation", text)
        self.assertNotIn("Workbook", text)
        self.assertTrue(text.endswith("Current question: What was revenue?"))


class StrictnessTests(unittest.TestCase):
    def test_workbook_quote_must_match_one_cell(self):
        snap = snapshot()
        workbook_id = f"workbook:{snap.snapshot_id}"
        src = sources(snapshot=snap)
        src.call("read_workbook_range", {"sheet": "Model", "range": "B7:B9"}, 5)
        for quote in ("1,650.0", "1650", "215", "=B8/B7", "13.0%"):
            src.check_citation({"source_id": workbook_id, "locator": "Model!B7:B9", "quote": quote})
        for quote in ("50", "650", "1,650.0 215.0"):
            with self.assertRaises(ValueError, msg=quote):
                src.check_citation(
                    {"source_id": workbook_id, "locator": "Model!B7:B9", "quote": quote}
                )

    def test_proposal_content_is_checked(self):
        src = sources(snapshot=snapshot())
        src.call("read_source", {"source_id": RELEASE, "start_line": 59, "end_line": 64}, 5)
        self.assertIn("error", propose(src, new_content="=SUM(B1:B3"))
        self.assertIn("error", propose(src, new_content='="unclosed'))
        self.assertIn("error", propose(src, new_content="$1,661.5M"))
        self.assertIn("error", propose(src, new_content="9" * 400))
        self.assertIn("error", propose(src, new_content="=B6+1216.5"))
        self.assertIn("error", propose(src, cell="B9", new_content=0.2))
        self.assertNotIn(
            "error", propose(src, cell="D7", new_content="Q3 release guidance midpoint")
        )


class BatchProposalTests(unittest.TestCase):
    def test_one_call_proposes_several_cells(self):
        src = sources(snapshot=snapshot())
        src.call("read_source", {"source_id": RELEASE, "start_line": 59, "end_line": 64}, 5)
        result = src.call(
            "propose_cell_edits",
            {
                "edits": [
                    edit(cell="B7", new_content=1661.5),
                    edit(cell="B8", new_content=220.5),
                    edit(cell="B0", new_content=1),
                ]
            },
            5,
        )
        self.assertEqual([r.get("proposal_id") for r in result["results"]], ["P1", "P2", None])
        self.assertIn("error", result["results"][2])
        self.assertEqual([p["cell"] for p in src.proposals], ["B7", "B8"])
        self.assertIn("Nothing was written", result["note"])

    def test_batch_shape_is_validated(self):
        src = sources(snapshot=snapshot())
        self.assertIn("error", src.call("propose_cell_edits", {"edits": []}, 5))
        self.assertIn("error", src.call("propose_cell_edits", {"edits": [edit()] * 11}, 5))
        self.assertIn("error", src.call("propose_cell_edits", {"cell": "B7"}, 5))


if __name__ == "__main__":
    unittest.main()
