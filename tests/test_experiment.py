"""Cross-task money controls must survive interruption without automatic retries."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from provenance.experiment import main


class ExperimentTests(unittest.TestCase):
    def invoke(self, directory, execute, *, grading_error=False):
        directory = Path(directory)
        benchmark = directory / "benchmark.json"
        benchmark.write_text(
            json.dumps(
                {
                    "version": "test",
                    "source_hashes": {"s": "hash"},
                    "tasks": [
                        {"id": "one", "question": "question without gold", "split": "dev"},
                        {"id": "two", "question": "another question", "split": "dev"},
                    ],
                }
            )
        )
        model = SimpleNamespace(name="fake", input_rate=1, output_rate=1)
        argv = [
            "experiment",
            "--live",
            "--corpus",
            str(directory),
            "--benchmark",
            str(benchmark),
            "--tasks",
            "one",
            "two",
            "--budget-usd",
            "0.05",
            "--per-task-usd",
            "0.03",
            "--output",
            str(directory / "experiment"),
        ]
        with (
            patch("sys.argv", argv),
            patch("provenance.experiment.OpenRouterModel", return_value=model),
            patch(
                "provenance.experiment.Sources",
                return_value=SimpleNamespace(documents={"s": {"sha256": "hash"}}),
            ),
            patch("provenance.experiment.subprocess.check_output", side_effect=["revision", ""]),
            patch(
                "provenance.experiment.grade_packet_answer",
                side_effect=RuntimeError("grading failed") if grading_error else None,
                return_value={"mechanical_checks_passed": True},
            ),
            patch("provenance.experiment.run_graph", side_effect=execute),
            patch("builtins.print"),
        ):
            main()

    def test_reservation_survives_crash_and_output_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "experiment" / "experiment.json"

            def crash(*args):
                state = json.loads(ledger.read_text())
                self.assertEqual(state["attempts"][0]["status"], "pending")
                self.assertAlmostEqual(state["accounted_cost_usd"], 0.03)
                self.assertEqual(args[0], "question without gold")
                raise RuntimeError("simulated process interruption")

            with self.assertRaises(RuntimeError):
                self.invoke(tmp, crash)
            self.assertAlmostEqual(json.loads(ledger.read_text())["accounted_cost_usd"], 0.03)
            with self.assertRaises(FileExistsError):
                self.invoke(tmp, lambda *args: self.fail("must not retry pending run"))

    def test_uncertain_charge_stops_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def execute(*args):
                calls.append(args[0])
                return {
                    "status": "failed",
                    "stop_reason": "timeout",
                    "metrics": {"accounted_cost_usd": 0.02, "cost_uncertain": True},
                }

            self.invoke(tmp, execute)
            ledger = json.loads((Path(tmp) / "experiment" / "experiment.json").read_text())
            self.assertEqual(calls, ["question without gold"])
            self.assertEqual(ledger["status"], "stopped_for_billing_review")
            self.assertAlmostEqual(ledger["accounted_cost_usd"], 0.02)

    def test_remaining_budget_limits_next_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            budgets = []

            def execute(*args):
                budgets.append(args[3].budget_usd)
                return {
                    "status": "completed",
                    "stop_reason": None,
                    "metrics": {"accounted_cost_usd": args[3].budget_usd, "cost_uncertain": False},
                }

            self.invoke(tmp, execute)
            self.assertEqual(len(budgets), 2)
            self.assertAlmostEqual(budgets[0], 0.03)
            self.assertAlmostEqual(budgets[1], 0.02)
            ledger = json.loads((Path(tmp) / "experiment" / "experiment.json").read_text())
            self.assertAlmostEqual(ledger["accounted_cost_usd"], 0.05)

    def test_known_charge_is_saved_before_grading_failure(self):
        with tempfile.TemporaryDirectory() as tmp:

            def execute(*args):
                return {
                    "status": "failed",
                    "stop_reason": "reservation_exceeded",
                    "metrics": {"accounted_cost_usd": 0.04, "cost_uncertain": True},
                }

            with self.assertRaisesRegex(RuntimeError, "grading failed"):
                self.invoke(tmp, execute, grading_error=True)
            ledger = json.loads((Path(tmp) / "experiment" / "experiment.json").read_text())
            self.assertAlmostEqual(ledger["accounted_cost_usd"], 0.04)
            self.assertAlmostEqual(ledger["attempts"][0]["accounted_cost_usd"], 0.04)
