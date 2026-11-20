"""Synthetic-only contracts for full inventory, leakage, reference QA and scoring."""

import copy
import csv
import hashlib
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from provenance.benchmarks import canonical_hash
from provenance.daloopa import model_input, prepare, protected, reference, unit, validate
from provenance.daloopa_run import MAX_OUTPUT, BenchmarkSources, forbidden, plan, run_benchmark
from provenance.daloopa_score import REVIEW_FIELDS, interval, review_identity, score, score_task
from provenance.model import INSTRUCTIONS, ReplayModel
from provenance.sources import TOOL_SCHEMAS


def rows(count=30, reserved=False, conflict=False):
    data = []
    for i in range(count):
        for bot in range(6):
            data.append(
                {
                    "ticker": "AMD" if reserved and i == count - 1 else f"SYNTH{i:03}",
                    "chatbot": f"bot{bot}",
                    "question": "What was revenue in USD million in FY2024?",
                    "gt_answer": "Revenue in FY2024 was 120 USD million.",
                    "gt_num": "DO_NOT_TRUST",
                    "gt_src": "https://issuer.example/annual.pdf",
                    "currency": "USD",
                    "category": f"category{i % 5}",
                    "difficulty": "hard" if i % 2 else "easy",
                    "answer": "HISTORICAL_ANSWER_SECRET",
                    "answer_num": "999999",
                }
            )
    if conflict:
        data[0]["gt_answer"] = "Conflicting 121 USD million."
    return data


def bundle(data=None):
    data = rows() if data is None else data
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(data[0]))
    writer.writeheader()
    writer.writerows(data)
    raw = output.getvalue().encode()
    source = {
        "dataset": "daloopa",
        "revision": "a" * 40,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "question_count": len({r["ticker"] for r in data}),
    }
    return prepare(raw, source)


def fake_model():
    return SimpleNamespace(
        name="test",
        mode="offline_test",
        instructions=INSTRUCTIONS,
        tool_schemas=TOOL_SCHEMAS,
        max_output=MAX_OUTPUT,
        input_rate=1,
        output_rate=1,
    )


def corpus(root):
    path = root / "corpus"
    path.mkdir()
    text = "Revenue FY2024: 120 USD million.\n"
    (path / "acme.txt").write_text(text)
    (path / "sources.json").write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "acme",
                        "company": "Synthetic",
                        "title": "Annual results",
                        "url": "https://issuer.example/annual.pdf",
                        "text_file": "acme.txt",
                        "sha256": hashlib.sha256(text.encode()).hexdigest(),
                    }
                ]
            }
        )
    )
    return path


def answer(value=120, unit_text="USD million"):
    return {
        "answerable": True,
        "answer": "Revenue was 120 USD million.",
        "claims": [
            {
                "key": "requested_answer",
                "value": value,
                "unit": unit_text,
                "period": "FY2024",
                "citations": [{"source_id": "acme", "locator": "L1", "quote": "120 USD million"}],
            }
        ],
    }


def record(value=120, unit_text="USD million"):
    text = "Revenue FY2024: 120 USD million.\n"
    prompt = json.dumps(model_input(bundle(rows(1))["tasks"][0]))
    result = answer(value, unit_text)
    return {
        "status": "completed",
        "report": {
            "status": "completed",
            "question": prompt,
            "answer": result,
            "events": [
                {"event": "run_started", "question": prompt},
                {
                    "event": "tool_request",
                    "call": {
                        "call_id": "r1",
                        "name": "read_source",
                        "arguments": json.dumps(
                            {"source_id": "acme", "start_line": 1, "end_line": 1}
                        ),
                    },
                },
                {
                    "event": "tool_result",
                    "call_id": "r1",
                    "result": {
                        "id": "acme",
                        "lines": [{"line": 1, "text": text.strip()}],
                        "sha256": hashlib.sha256(text.encode()).hexdigest(),
                    },
                },
                {
                    "event": "model_response",
                    "response": {
                        "output": [
                            {
                                "type": "message",
                                "content": [{"type": "output_text", "text": json.dumps(result)}],
                            }
                        ]
                    },
                },
                {"event": "run_finished", "status": "completed"},
            ],
        },
        "evidence": {"documents": {"acme": {"text": text}}},
    }


def submission(data, profile="quick"):
    return {
        "prepared_sha256": canonical_hash(data["manifest"]),
        "profile": profile,
        "records": [
            {"id": key, "status": "not_started"} for key in data["manifest"][f"{profile}_ids"]
        ],
    }


class DaloopaPreparationTests(unittest.TestCase):
    def test_full_inventory_quick_stable_no_gold_projection(self):
        data = bundle(rows(40, reserved=True, conflict=True))
        validate(data)
        self.assertEqual(len(data["tasks"]), 40)
        self.assertEqual(len(data["manifest"]["quick_ids"]), 25)
        self.assertEqual(data, bundle(rows(40, reserved=True, conflict=True)))
        safe = json.dumps(data["inputs"])
        for secret in ("HISTORICAL_ANSWER_SECRET", "DO_NOT_TRUST", "gt_src", "reference"):
            self.assertNotIn(secret, safe)
        self.assertEqual(len(data["inputs"]), 39)  # Full runs unresolved questions too.
        reserved = next(t for t in data["tasks"] if t["ticker"] == "AMD")
        self.assertIsNone(model_input(reserved))
        self.assertNotIn("question", reserved)
        self.assertIsNone(reserved["reference"])
        full = plan(data, "full")
        self.assertEqual(full["selected"], 40)
        self.assertEqual(full["dispositions"]["reserved_issuer"], 1)

    def test_hash_and_input_tampering_fails(self):
        original = bundle()
        for mutate in (
            lambda d: d["inputs"][0].update(gold="LEAK"),
            lambda d: d["tasks"][0]["reference"].update(value="999"),
            lambda d: d["manifest"]["quick_ids"].reverse(),
            lambda d: d["manifest"]["full_ids"].pop(),
        ):
            data = copy.deepcopy(original)
            mutate(data)
            with self.assertRaises(ValueError):
                validate(data)

    def test_reference_parser_ignores_urls_years_and_upstream_parsed_value(self):
        r = rows(1)[0]
        r["gt_answer"] = "FY2024 revenue: [120](https://issuer.example/9999) USD million."
        self.assertEqual(reference([r])["value"], "120000000")
        r["gt_answer"] = "FY2024 revenue: $1.5 billion."
        self.assertEqual(reference([r])["value"], "1500000000.0")
        r["gt_answer"] = "FY2024 revenue: 120 and 121 USD million."
        self.assertEqual(reference([r])["status"], "reference_review_required")
        r["gt_answer"] = "FY2024 revenue: (120) USD million."
        self.assertEqual(reference([r])["value"], "-120000000")

    def test_markdown_currency_does_not_erase_negative_sign(self):
        r = rows(1)[0]
        r["gt_answer"] = "FY2024 revenue was -[$365 million](https://issuer.example/123)."
        self.assertEqual(reference([r])["value"], "-365000000")
        r["gt_answer"] = "FY2024 revenue was [-$365 million](https://issuer.example/123)."
        self.assertEqual(reference([r])["value"], "-365000000")
        r["gt_answer"] = "FY2024 revenue was -[365 USD million](https://issuer.example/123)."
        self.assertEqual(reference([r])["value"], "-365000000")

    def test_reference_periods_do_not_remove_nonperiod_numbers(self):
        r = rows(1)[0]
        r.update(
            question="What was revenue from the 10 stores in USD in 2024?",
            gt_answer="10 USD in 2023",
        )
        self.assertEqual(reference([r])["status"], "reference_review_required")
        r["gt_answer"] = "10 USD in 2024."
        self.assertEqual(reference([r])["value"], "10")
        r.update(
            question="What was revenue in USD in Q3 2024?", gt_answer="Q3 2024 revenue was USD 10."
        )
        self.assertEqual(reference([r])["value"], "10")
        self.assertEqual(unit("USD trillion", strict=True), ("USD", Decimal("1000000000000")))
        self.assertEqual(unit("USD/share", strict=True), ("USD/share", Decimal(1)))
        self.assertEqual(unit("USD per square foot", strict=True), ("USD/square foot", Decimal(1)))
        with self.assertRaises(ValueError):
            unit("USD per mystery", strict=True)

    def test_all_500_cases_preserved(self):
        data = bundle(rows(500, reserved=True, conflict=True))
        self.assertEqual(plan(data, "full")["selected"], 500)
        self.assertEqual(plan(data, "quick")["selected"], 25)
        self.assertEqual(len(data["inputs"]), 499)

    def test_reserved_ticker_aliases(self):
        for name in ("AMD", "NASDAQ:MSFT", "AMZN:US", "SQ", "XYZ", "CASY", "ODFL", "AEE"):
            self.assertTrue(protected(name))
            self.assertTrue(forbidden({"company": name}))
        self.assertTrue(forbidden({"title": "AMZN 2024 revenue"}))
        self.assertTrue(forbidden({"url": "https://datasets.huggingface.co/answers"}))
        self.assertFalse(forbidden({"company": "Synthetic", "url": "https://issuer.example"}))

    def test_unit_dimensions_scales_and_rejection(self):
        for name, expected in {
            "USD million": ("USD", "1000000"),
            "INR Crore": ("INR", "10000000"),
            "USD cents": ("USD", "0.01"),
            "USD per share": ("USD/share", "1"),
            "percent": ("percent", "1"),
            "basis points": ("percentage_point", "0.01"),
        }.items():
            self.assertEqual(unit(name), (expected[0], Decimal(expected[1])))
        self.assertEqual(unit("%", strict=True), ("percent", Decimal(1)))
        self.assertEqual(unit("basis points", strict=True), ("percentage_point", Decimal("0.01")))
        for name in ("USD EUR", "nonsense", "USD million thousand"):
            with self.assertRaises(ValueError):
                unit(name)


class DaloopaScoreTests(unittest.TestCase):
    def setUp(self):
        self.task = bundle(rows(1))["tasks"][0]

    def test_exact_conversion_wrong_currency_sign_and_no_incidental_matching(self):
        for value, u, correct in [
            (120, "USD million", True),
            (120000, "USD thousand", True),
            (-120, "USD million", False),
            (120, "EUR million", False),
            (120, "USD per share", False),
            (120, "USD", False),
        ]:
            self.assertIs(score_task(self.task, record(value, u))["numeric_exact"], correct)
        r = record()
        r["report"]["answer"]["claims"].append(copy.deepcopy(r["report"]["answer"]["claims"][0]))
        self.assertFalse(score_task(self.task, r)["numeric_exact"])
        for value in (True, float("nan"), float("inf"), "120 million"):
            self.assertFalse(score_task(self.task, record(value))["numeric_exact"])

    def test_exact_zero_and_tolerance_denominator(self):
        self.task["reference"]["value"] = "0"
        self.assertTrue(score_task(self.task, record(0))["tolerance_1pct"])
        self.assertFalse(score_task(self.task, record(0.001))["tolerance_5pct"])
        self.task["reference"]["value"] = "120000000"
        self.assertTrue(score_task(self.task, record(121))["tolerance_1pct"])
        self.assertFalse(score_task(self.task, record(122))["tolerance_1pct"])
        self.assertTrue(score_task(self.task, record(122))["tolerance_5pct"])

    def test_quotes_do_not_imply_support_and_review_cannot_drift(self):
        r = record()
        result = score_task(self.task, r)
        self.assertTrue(result["quote_valid"])
        self.assertIsNone(result["supported_correct"])
        review = {
            **review_identity(self.task, r),
            "reviewer": "test reviewer",
            "reviewer_kind": "agent",
            "notes": "Synthetic verification",
            **dict.fromkeys(REVIEW_FIELDS, True),
        }
        self.assertTrue(score_task(self.task, r, review)["supported_correct"])
        r["report"]["answer"]["claims"][0]["period"] = "FY2023"
        with self.assertRaisesRegex(ValueError, "mismatched"):
            score_task(self.task, r, review)
        bad = record()
        bad["evidence"]["documents"]["acme"]["text"] = "Changed evidence"
        self.assertFalse(score_task(self.task, bad)["quote_valid"])

    def test_all_selected_cases_remain_in_denominator(self):
        data = bundle(rows(30, reserved=True, conflict=True))
        run = submission(data, "full")
        report = score(data, run)
        self.assertEqual(report["selected_count"], 30)
        self.assertEqual(report["scorable_count"], 28)
        self.assertEqual(report["numeric_match_accuracy"], 0)
        self.assertIsNone(report["full_selection_numeric_accuracy"])
        self.assertIsNone(report["supported_accuracy"])
        run["records"].pop()
        with self.assertRaises(ValueError):
            score(data, run)
        self.assertIsNone(interval(0, 0))
        self.assertLess(interval(25, 25)[0], 1)


class DaloopaRunnerTests(unittest.TestCase):
    def test_reserved_corpus_rejected_before_file_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sources.json").write_text(
                json.dumps({"sources": [{"company": "MSFT", "text_file": "DOES_NOT_EXIST"}]})
            )
            with self.assertRaisesRegex(ValueError, "reserved"):
                BenchmarkSources(root)

    def test_full_executes_unscored_cases_and_stops_on_uncertain_cost(self):
        data = bundle(rows(4, reserved=True, conflict=True))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls = []

            def execute(prompt, model, sources, limits, trace):
                calls.append(prompt)
                self.assertNotIn("DO_NOT_TRUST", prompt)
                self.assertNotIn("HISTORICAL_ANSWER_SECRET", prompt)
                ledger = json.loads((root / "run/submission.json").read_text())
                self.assertEqual(sum(r["status"] == "pending" for r in ledger["records"]), 1)
                return {
                    "status": "failed",
                    "answer": None,
                    "stop_reason": "provider error",
                    "metrics": {"accounted_cost_usd": 0.03, "cost_uncertain": True},
                }

            result = run_benchmark(
                data,
                fake_model(),
                root / "run",
                profile="full",
                corpus=corpus(root),
                execute=execute,
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(result["status"], "stopped_for_billing_review")
            self.assertEqual(len(result["records"]), 4)
            self.assertEqual(result["records"][-1]["status"], "skipped")
            self.assertIn("reserved_issuer", [r["status"] for r in result["records"]])
            with self.assertRaises(FileExistsError):
                run_benchmark(
                    data, fake_model(), root / "run", corpus=root / "corpus", execute=execute
                )

    def test_crash_retains_pending_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(RuntimeError):
                run_benchmark(
                    bundle(rows(1)),
                    fake_model(),
                    root / "run",
                    corpus=corpus(root),
                    execute=Mock(side_effect=RuntimeError("crash")),
                )
            ledger = json.loads((root / "run/submission.json").read_text())
            self.assertEqual(ledger["records"][0]["status"], "pending")
            self.assertTrue(ledger["records"][0]["cost_uncertain"])
            self.assertEqual(ledger["accounted_cost_usd"], 0.05)

    def test_actual_graph_replay_produces_reproducible_score(self):
        read = {
            "status": "completed",
            "output": [
                {
                    "type": "function_call",
                    "name": "read_source",
                    "call_id": "r1",
                    "arguments": json.dumps({"source_id": "acme", "start_line": 1, "end_line": 1}),
                }
            ],
        }
        final = {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(answer())}],
                }
            ],
        }
        model = ReplayModel([read, final])
        for key, value in vars(fake_model()).items():
            setattr(model, key, value)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = bundle(rows(1))
            result = run_benchmark(data, model, root / "run", corpus=corpus(root))
            report = score(data, result)
            self.assertEqual(report["numeric_match_accuracy"], 1)
            self.assertTrue(report["tasks"][0]["quote_valid"])
            self.assertIsNone(report["supported_accuracy"])
            self.assertEqual(report, json.loads((root / "run/score.json").read_text()))

    def test_web_results_exclude_answer_sites_before_model_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = BenchmarkSources(corpus(root), exa_key="synthetic", exa_cap=0.01)
            sources.documents["bad"] = {"id": "bad", "url": "https://huggingface.co/answers"}
            with patch(
                "provenance.exa_sources.ExaSources.search",
                return_value={"results": [{"id": "bad"}, {"id": "acme"}], "mode": "corpus+web"},
            ):
                self.assertEqual(sources.search("revenue", 1)["results"], [{"id": "acme"}])
            self.assertNotIn("bad", sources.documents)
