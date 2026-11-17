"""Offline adversarial checks for application receipts and profile migration."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from provenance.agent import Limits, Trace
from provenance.context import project_messages
from provenance.controls import Budget
from provenance.evaluation import validate_report_evidence
from provenance.graph import run_graph
from provenance.langchain_model import OpenRouterModel, chat_messages
from provenance.receipts import (
    PROFILE,
    digest,
    make_receipt,
    verify_receipt,
    verify_report_receipts,
)
from provenance.sources import TOOL_SCHEMAS, Sources


def result(content=None, *, calls=None, usage=True, finish="stop"):
    return AIMessage(
        content=content or "",
        tool_calls=calls or [],
        usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
        if usage
        else None,
        response_metadata={"finish_reason": finish},
    )


def abstention():
    return result('{"answerable":false,"answer":"Evidence missing","claims":[]}')


def read_call():
    return result(
        calls=[
            {
                "id": "r1",
                "name": "read_source",
                "args": {"source_id": "acme", "start_line": 1, "end_line": 1},
            }
        ]
    )


def model_with(responses, **kwargs):
    chat = Mock()
    chat.bind_tools.return_value.bind.return_value.invoke.side_effect = responses
    chat.bind.return_value.invoke.side_effect = responses
    return OpenRouterModel("SECRET_API_VALUE", "test", 1, 2, chat=chat, **kwargs), chat


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        text = "Revenue FY2024: 120 USD million.\n"
        import hashlib

        (self.root / "acme.txt").write_text(text)
        self.manifest = {
            "sources": [
                {
                    "id": "acme",
                    "title": "Acme",
                    "text_file": "acme.txt",
                    "sha256": hashlib.sha256(text.encode()).hexdigest(),
                }
            ]
        }
        self.write_manifest()

    def write_manifest(self):
        (self.root / "sources.json").write_text(json.dumps(self.manifest))

    def sources(self):
        return Sources(self.root)

    def capture(self, model, history, *, budget=1, final_only=False):
        events = []
        response = model.step_with_receipt(
            history,
            2,
            Budget(budget),
            run_id="run",
            attempt_id=1,
            emit=lambda kind, **data: events.append({"event": kind, **data}),
            final_only=final_only,
        )
        return response, events

    def test_adapter_parity_and_immutable_capture(self):
        history = [{"role": "user", "content": "Revenue?"}]
        plain, plain_chat = model_with([abstention()])
        captured, captured_chat = model_with([abstention()])
        first_budget, second_budget = Budget(1), Budget(1)
        first = plain.step(history, 2, first_budget)
        events = []
        second = captured.step_with_receipt(
            history,
            2,
            second_budget,
            run_id="run",
            attempt_id=1,
            emit=lambda kind, **data: events.append({"event": kind, **data}),
        )
        self.assertEqual(first, second)
        self.assertEqual(first_budget.charged, second_budget.charged)
        self.assertEqual(plain_chat.mock_calls, captured_chat.mock_calls)
        receipt = events[0]["receipt"]
        verify_receipt(receipt)
        actual = captured_chat.bind_tools.return_value.bind.return_value.invoke.call_args.args[0]
        self.assertEqual(
            receipt["request"]["messages"], [m.model_dump(mode="json") for m in actual]
        )
        history[0]["content"] = "changed after dispatch"
        self.assertEqual(receipt["canonical_history"][0]["content"], "Revenue?")
        self.assertNotIn("SECRET_API_VALUE", json.dumps(events))

    def test_inventory_uses_actual_projection_not_source_marker(self):
        history = [{"role": "user", "content": "Revenue?"}]
        for identifier, name, output in [
            ("s1", "search", {"hits": []}),
            (
                "r1",
                "read_source",
                {
                    "id": "acme",
                    "locator": "L1-L1",
                    "lines": [{"line": 1, "text": "omitted_from_model_context"}],
                    "omitted_from_model_context": True,
                },
            ),
            ("s2", "search", {"hits": []}),
            ("r2", "read_source", {"error": "not available"}),
        ]:
            history.extend(
                [
                    {
                        "type": "function_call",
                        "call_id": identifier,
                        "name": name,
                        "arguments": "not-json",
                    },
                    {
                        "type": "function_call_output",
                        "call_id": identifier,
                        "output": json.dumps(output),
                    },
                ]
            )
        model, _ = model_with([abstention()])
        _, events = self.capture(model, history)
        receipt = events[0]["receipt"]
        verify_receipt(receipt)
        self.assertEqual(receipt["omitted_call_ids"], ["s1"])
        self.assertEqual(receipt["retained_call_ids"], ["r1", "s2", "r2"])
        self.assertEqual([f["call_id"] for f in receipt["legacy_read_fragments"]], ["r1"])

    def test_grouped_calls_and_unanswered_call(self):
        history = [
            {"type": "function_call", "call_id": identifier, "name": "search", "arguments": "{"}
            for identifier in ("a", "b")
        ]
        model, _ = model_with([abstention()])
        _, events = self.capture(model, history)
        receipt = events[0]["receipt"]
        verify_receipt(receipt)
        self.assertEqual(receipt["retained_call_ids"], [])
        self.assertEqual(len(receipt["request"]["messages"]), 2)
        self.assertEqual(
            len(receipt["request"]["messages"][1]["additional_kwargs"]["tool_calls"]), 2
        )

    def test_tampering_rejected_even_with_recomputed_digest(self):
        model, _ = model_with([abstention()])
        _, events = self.capture(model, [{"role": "user", "content": "Revenue?"}])
        for field in (
            "retained_call_ids",
            "legacy_read_fragments",
            "projected_messages",
            "request",
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(events[0]["receipt"])
                if field == "request":
                    changed[field]["messages"][0]["content"] = "forged"
                    changed["request_sha256"] = digest(changed[field])
                else:
                    changed[field].append({"forged": True})
                with self.assertRaises(ValueError):
                    verify_receipt(changed)

    def test_constructor_schema_snapshot_and_bound_drift(self):
        schemas = copy.deepcopy(TOOL_SCHEMAS)
        model, _ = model_with([abstention()], tool_schemas=schemas)
        before = model.receipt_policy()
        schemas[0]["description"] = "external mutation"
        self.assertEqual(model.receipt_policy(), before)
        model.tool_schemas[0]["description"] = "internal mutation"
        with self.assertRaisesRegex(ValueError, "bound tools"):
            model.receipt_policy()

    def test_failed_provider_and_spend_rejection_retain_receipts(self):
        for outcome in (
            TimeoutError("SECRET_API_VALUE"),
            result(usage=False),
            result(finish="length"),
            KeyboardInterrupt(),
        ):
            with self.subTest(outcome=type(outcome).__name__):
                model, _ = model_with([outcome])
                report = run_graph("Revenue?", model, self.sources(), runtime_profile=PROFILE)
                self.assertIn(report["status"], ("failed", "stopped"))
                self.assertEqual(verify_report_receipts(report)["receipts"], 1)
                self.assertNotIn("SECRET_API_VALUE", json.dumps(report))
        model, chat = model_with([abstention()])
        report = run_graph(
            "Revenue?", model, self.sources(), Limits(budget_usd=0.000001), runtime_profile=PROFILE
        )
        self.assertEqual(report["stop_reason"], "spend_limit")
        self.assertEqual(verify_report_receipts(report)["receipts"], 1)
        self.assertFalse(any(e["event"] == "model_dispatch_started" for e in report["events"]))
        chat.bind_tools.return_value.bind.assert_not_called()

    def test_final_synthesis_and_repair_receipts(self):
        model, _ = model_with([read_call(), result("invalid-json"), abstention()])
        report = run_graph(
            "Revenue?", model, self.sources(), Limits(max_model_calls=3), runtime_profile=PROFILE
        )
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["metrics"]["answer_retries"], 1)
        self.assertEqual(verify_report_receipts(report)["receipts"], 3)
        receipts = [e["receipt"] for e in report["events"] if e["event"] == "model_input_receipt"]
        self.assertEqual(receipts[-1]["request"]["options"]["tool_choice"], "none")
        self.assertEqual(receipts[-1]["legacy_read_fragments"][0]["locator"], "L1-L1")

    def test_report_missing_or_modified_receipt_rejected(self):
        model, _ = model_with([read_call(), abstention()])
        report = run_graph("Revenue?", model, self.sources(), runtime_profile=PROFILE)
        for modification in ("remove", "history", "count"):
            changed = copy.deepcopy(report)
            if modification == "remove":
                changed["events"] = [
                    e for e in changed["events"] if e["event"] != "model_input_receipt"
                ]
            elif modification == "count":
                changed["metrics"]["model_calls"] += 1
            else:
                receipt = [
                    e["receipt"] for e in changed["events"] if e["event"] == "model_input_receipt"
                ][-1]
                receipt["run_id"] = "different-run"
            with self.assertRaises(ValueError):
                verify_report_receipts(changed)

    def test_pause_resume_and_cached_result(self):
        options = {
            "checkpoint_path": self.root / "run.db",
            "thread_id": "test",
            "runtime_profile": PROFILE,
        }
        model, _ = model_with([read_call()])
        paused = run_graph("Revenue?", model, self.sources(), pause_after_tools=True, **options)
        self.assertEqual(paused["status"], "paused")
        model, _ = model_with([abstention()])
        completed = run_graph("Revenue?", model, self.sources(), resume=True, **options)
        self.assertEqual(completed["run_id"], paused["run_id"])
        self.assertEqual(verify_report_receipts(completed)["receipts"], 2)
        model, chat = model_with([])
        cached = run_graph("Revenue?", model, self.sources(), resume=True, **options)
        self.assertEqual(cached, completed)
        chat.bind_tools.return_value.bind.assert_not_called()

    def test_checkpoint_metadata_and_prompt_generation_drift(self):
        options = {
            "checkpoint_path": self.root / "drift.db",
            "thread_id": "test",
            "runtime_profile": PROFILE,
        }
        model, _ = model_with([read_call()])
        run_graph("Revenue?", model, self.sources(), pause_after_tools=True, **options)
        for field, value in (
            ("title", "different"),
            ("published", "2024-01-01"),
            ("extraction", {"warning": "changed"}),
            ("sidecar_sha256", "new"),
            ("line_locations", [{"page": 2}]),
        ):
            with self.subTest(field=field):
                self.manifest["sources"][0][field] = value
                self.write_manifest()
                model, chat = model_with([])
                with self.assertRaisesRegex(ValueError, "differs"):
                    run_graph("Revenue?", model, self.sources(), resume=True, **options)
                chat.bind_tools.return_value.bind.assert_not_called()
                self.manifest["sources"][0].pop(field)
                if field == "title":
                    self.manifest["sources"][0][field] = "Acme"
        self.write_manifest()
        for kwargs in ({"instructions": "Different"}, {"max_output": 100}, {"tool_schemas": []}):
            model, chat = model_with([], **kwargs)
            with self.assertRaisesRegex(ValueError, "differs"):
                run_graph("Revenue?", model, self.sources(), resume=True, **options)
            chat.bind_tools.return_value.bind.assert_not_called()

    def test_legacy_checkpoint_cannot_be_upgraded(self):
        options = {"checkpoint_path": self.root / "legacy.db", "thread_id": "test"}
        model, _ = model_with([read_call()])
        run_graph("Revenue?", model, self.sources(), pause_after_tools=True, **options)
        model, _ = model_with([])
        with self.assertRaisesRegex(ValueError, "Unsupported checkpoint profile"):
            run_graph(
                "Revenue?", model, self.sources(), resume=True, runtime_profile=PROFILE, **options
            )
        model, _ = model_with([abstention()])
        legacy = run_graph("Revenue?", model, self.sources(), resume=True, **options)
        self.assertEqual(legacy["status"], "completed")
        self.assertNotIn("runtime_profile", legacy)

    def test_explicit_log_persists_failed_request(self):
        model, _ = model_with([TimeoutError()])
        trace = Trace(self.root / "logs")
        report = run_graph("Revenue?", model, self.sources(), trace=trace, runtime_profile=PROFILE)
        saved = json.loads((trace.directory / "result.json").read_text())
        self.assertEqual(saved, report)
        self.assertEqual(verify_report_receipts(saved)["receipts"], 1)

    def test_cli_rejects_unsupported_profile_before_credentials(self):
        run = subprocess.run(
            [sys.executable, "-m", "provenance", "demo", "--runtime-profile", PROFILE],
            capture_output=True,
            text=True,
        )
        self.assertEqual(run.returncode, 2)
        self.assertIn("Receipt profile requires", run.stderr)

    def test_profile_downgrade_and_malformed_trace_rejected(self):
        model, _ = model_with([read_call(), abstention()])
        report = run_graph("Revenue?", model, self.sources(), runtime_profile=PROFILE)
        task = {"question": "Revenue?", "source_ids": ["acme"]}
        changed = copy.deepcopy(report)
        changed.pop("runtime_profile")
        changed["events"] = [
            e
            for e in changed["events"]
            if e["event"]
            not in {"model_input_receipt", "model_dispatch_started", "model_attempt_finished"}
        ]
        with self.assertRaises(ValueError):
            validate_report_evidence(task, changed, directory=self.root)
        for events in ([], [None], {}, None):
            with self.assertRaises(ValueError):
                validate_report_evidence(task, {**report, "events": events}, directory=self.root)

    def test_policy_and_trace_boundary_tampering_rejected(self):
        model, _ = model_with([abstention()])
        report = run_graph("Revenue?", model, self.sources(), runtime_profile=PROFILE)
        for field in ("instructions", "adapter_version", "bound_tools_sha256", "ending"):
            changed = copy.deepcopy(report)
            if field == "ending":
                changed["events"].pop()
            elif field == "instructions":
                changed["events"][0][field] = "forged"
            else:
                changed["events"][0]["receipt_policy"][field] = "forged"
            with self.assertRaises(ValueError):
                verify_report_receipts(changed)

    def test_rebuilt_receipt_cannot_drop_canonical_history(self):
        model, _ = model_with([read_call(), abstention()])
        report = run_graph("Revenue?", model, self.sources(), runtime_profile=PROFILE)
        request = [e for e in report["events"] if e["event"] == "model_request"][-1]
        event = [e for e in report["events"] if e["event"] == "model_input_receipt"][-1]
        old = event["receipt"]
        history = [{"role": "user", "content": "Unrelated question"}]
        request["input"] = history
        event["receipt"] = make_receipt(
            history,
            project_messages(history),
            chat_messages(history, instructions=old["instructions"]),
            instructions=old["instructions"],
            schemas=old["tool_schemas"],
            config=old["request"]["config"],
            run_id=old["run_id"],
            attempt_id=old["attempt_id"],
            timeout=old["request"]["options"]["timeout"],
            final_only=old["final_only"],
        )
        verify_receipt(event["receipt"])
        with self.assertRaisesRegex(ValueError, "discontinuous"):
            verify_report_receipts(report)

    def test_real_injected_client_settings_must_match(self):
        client = ChatOpenAI(
            api_key="dummy", model="other", temperature=0.8, max_tokens=99, max_retries=2
        )
        model = OpenRouterModel("dummy", "declared", 1, 2, chat=client)
        with self.assertRaisesRegex(ValueError, "matching OpenRouter"):
            model.receipt_policy()
        model = OpenRouterModel("dummy", "test", 1, 2)
        self.assertEqual(model.receipt_policy()["config"]["client_kind"], "ChatOpenAI")
        model._receipt_client.temperature = 0.8
        with self.assertRaises(ValueError):
            model.receipt_policy()
