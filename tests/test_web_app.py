import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from provenance.web.app import create_app
from provenance.web.worker import TurnRunner
from tests.web_helpers import offline_worker

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "data/demo/cloudflare-fy2024-model.xlsx"
Q1 = (
    "What revenue did Cloudflare report for Q3 2024, and what full-year 2024 revenue "
    "guidance did management give?"
)
Q2 = (
    "Does the FY2024 revenue assumption in my model match management's latest guidance? "
    "If not, propose an update."
)
LIVE_ENV = {
    "EXA_API_KEY": "exa-test-SECRET123",
    "EXA_MAX_REQUEST_USD": "0.03",
    "OPENROUTER_API_KEY": "sk-or-test-SECRET123",
    "OPENROUTER_MODEL": "test/model",
    "OPENROUTER_INPUT_USD_PER_MILLION": "0.30",
    "OPENROUTER_OUTPUT_USD_PER_MILLION": "1.20",
}
NO_LIVE_ENV = {**{key: "" for key in LIVE_ENV}, "WEB_ACCESS_CODE": ""}


def read_events(client, sid, tid, last_id=None):
    headers = {"Last-Event-ID": str(last_id)} if last_id is not None else {}
    received, current = [], {}
    url = f"/api/sessions/{sid}/turns/{tid}/events"
    with client.stream("GET", url, headers=headers) as response:
        assert response.status_code == 200, response.read()
        for line in response.iter_lines():
            if not line:
                if current:
                    received.append(current)
                    if current.get("event") == "done":
                        break
                current = {}
                continue
            key, _, value = line.partition(": ")
            current[key] = value
    return received


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env = mock.patch.dict(os.environ, {**LIVE_ENV, "WEB_ACCESS_CODE": ""})
        self.env.start()
        self.addCleanup(self.env.stop)

    def client(self, **kwargs):
        kwargs.setdefault("runner", TurnRunner(target=offline_worker))
        app = create_app(
            ledger_path=Path(self.directory.name) / "ledger.jsonl",
            export_dir=Path(self.directory.name) / "exports",
            **kwargs,
        )
        return TestClient(app)

    def session(self, client, corpus="live-web"):
        response = client.post("/api/sessions", json={"corpus": corpus})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["id"]

    def run_turn(self, client, sid, question, mode="live"):
        response = client.post(
            f"/api/sessions/{sid}/turns", json={"question": question, "mode": mode}
        )
        self.assertEqual(response.status_code, 200, response.text)
        tid = response.json()["turn_id"]
        events = read_events(client, sid, tid)
        return tid, events, json.loads(events[-1]["data"])

    def upload(self, client, sid, data=None, name=FIXTURE.name):
        files = {
            "file": (name, io.BytesIO(data or FIXTURE.read_bytes()), "application/octet-stream")
        }
        return client.post(f"/api/sessions/{sid}/workbook", files=files)


class ConfigAndSourcesTests(AppTestCase):
    def test_explicit_turn_limit_is_reported_and_reserved(self):
        with mock.patch.dict(os.environ, {"WEB_MAX_TURN_USD": "0.07"}):
            with self.client() as client:
                self.assertEqual(client.get("/api/config").json()["limits"]["max_turn_usd"], 0.07)
                sid = self.session(client)
                with mock.patch("provenance.web.app.Ledger.reserve", return_value=None) as reserve:
                    response = client.post(
                        f"/api/sessions/{sid}/turns", json={"question": "Research", "mode": "live"}
                    )
                    self.assertEqual(response.status_code, 409)
                    reserve.assert_called_once_with(0.07)

    def test_invalid_turn_limit_rejected(self):
        for value in ("0", "-1", "nan", "inf"):
            with (
                self.subTest(value=value),
                mock.patch.dict(os.environ, {"WEB_MAX_TURN_USD": value}),
            ):
                with self.assertRaises(ValueError):
                    self.client()

    def test_config_lists_corpora_without_secrets(self):
        with mock.patch.dict(os.environ, LIVE_ENV):
            response = self.client().get("/api/config")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("SECRET123", response.text)
        config = response.json()
        self.assertTrue(config["live_available"])
        self.assertEqual(config["model"], "test/model")
        self.assertEqual(config["spend"]["cap_usd"], 1.0)
        ids = [corpus["id"] for corpus in config["corpora"]]
        self.assertEqual(ids, ["live-web"])
        cloudflare = config["corpora"][0]
        self.assertFalse(config["replay"])
        self.assertEqual(cloudflare["starters"], [])
        self.assertEqual(cloudflare["documents"], [])

    def test_live_unavailable_without_key(self):
        with mock.patch.dict(os.environ, NO_LIVE_ENV):
            self.assertFalse(self.client().get("/api/config").json()["live_available"])

    def test_source_window(self):
        runner = FakeRunner()
        client = self.client(runner=runner)
        sid = self.session(client)
        client.post(f"/api/sessions/{sid}/turns", json={"question": "Find revenue"})
        document = {
            "id": "web-test",
            "title": "Live result",
            "url": "https://example.com/report",
            "text": "Revenue was 100.\nGuidance was 110.",
        }
        runner.finish([], documents={"web-test": document})
        url = "/api/sources/live-web/web-test"
        window = client.get(url, params={"start": 1, "end": 2}).json()
        self.assertFalse(window["has_original"])
        self.assertEqual(window["lines"][1]["text"], "Guidance was 110.")
        self.assertEqual(window["url"], document["url"])
        self.assertEqual(
            client.get(f"/api/sessions/{sid}").json()["documents"][0]["title"], "Live result"
        )
        self.assertEqual(client.get(url, params={"start": 1, "end": 300}).status_code, 400)
        self.assertEqual(client.get("/api/sources/live-web/nope").status_code, 404)
        self.assertEqual(client.get("/api/sources/nope/x").status_code, 404)
        self.assertEqual(client.get(url + "/original").status_code, 404)
        client.post(f"/api/sessions/{sid}/turns", json={"question": "Explain guidance"})
        self.assertEqual(runner.pending[0][1]["documents"], {"web-test": document})

    def test_live_requires_exa_key_and_positive_cap(self):
        for missing in (
            {"EXA_API_KEY": ""},
            {"EXA_MAX_REQUEST_USD": "0"},
            {"EXA_MAX_REQUEST_USD": "invalid"},
        ):
            with self.subTest(missing=missing), mock.patch.dict(os.environ, missing):
                client = self.client()
                self.assertFalse(client.get("/api/config").json()["live_available"])
                sid = self.session(client)
                response = client.post(f"/api/sessions/{sid}/turns", json={"question": "Revenue?"})
                self.assertEqual(response.status_code, 409)
                self.assertIn("EXA_API_KEY", response.json()["detail"])


class AccessGateTests(AppTestCase):
    def test_access_code_gate(self):
        with mock.patch.dict(os.environ, {"WEB_ACCESS_CODE": "tulip-42"}):
            client = self.client()
        self.assertEqual(client.get("/api/auth").json(), {"required": True, "authenticated": False})
        self.assertEqual(client.get("/api/config").status_code, 401)
        self.assertEqual(
            client.post("/api/sessions", json={"corpus": "cloudflare-2024-q3"}).status_code, 401
        )
        self.assertEqual(client.post("/api/login", json={"code": "nope"}).status_code, 401)
        login = client.post("/api/login", json={"code": " tulip-42 "})
        self.assertEqual(login.status_code, 200)
        self.assertIn("httponly", login.headers["set-cookie"].lower())
        self.assertEqual(client.get("/api/config").status_code, 200)
        self.assertTrue(client.get("/api/auth").json()["authenticated"])
        self.assertEqual(self.session(client)[:0], "")

    def test_no_gate_without_code(self):
        client = self.client()
        self.assertEqual(client.get("/api/auth").json(), {"required": False, "authenticated": True})
        self.assertEqual(client.get("/api/config").status_code, 200)


class TurnTests(AppTestCase):
    def test_live_turn_streams_and_completes(self):
        client = self.client()
        sid = self.session(client)
        tid, events, view = self.run_turn(client, sid, Q1)
        kinds = [json.loads(e["data"])["kind"] for e in events if e.get("event") == "progress"]
        self.assertIn("search", kinds)
        self.assertIn("read", kinds)
        self.assertEqual(view["status"], "completed")
        self.assertEqual(view["mode"], "live_openrouter_langchain")
        self.assertEqual(view["answer"]["claims"][0]["value"], 430.1)
        session = client.get(f"/api/sessions/{sid}").json()
        self.assertEqual(session["turns"][0]["id"], tid)
        ledger = (Path(self.directory.name) / "ledger.jsonl").read_text()
        self.assertIn('"mode": "live"', ledger)

    def test_sse_resume_no_duplicates(self):
        client = self.client()
        sid = self.session(client)
        tid, events, _ = self.run_turn(client, sid, Q1)
        resumed = read_events(client, sid, tid, last_id=1)
        self.assertEqual(resumed[0]["id"], "2")
        self.assertEqual(len(resumed), len(events) - 2)

    def test_progress_polling(self):
        import time

        client = self.client()
        sid = self.session(client)
        tid = client.post(
            f"/api/sessions/{sid}/turns", json={"question": Q1, "mode": "live"}
        ).json()["turn_id"]
        url = f"/api/sessions/{sid}/turns/{tid}/progress"
        for _ in range(200):
            body = client.get(url, params={"after": -1}).json()
            if body["done"]:
                break
            time.sleep(0.1)
        self.assertTrue(body["done"])
        self.assertEqual(body["turn"]["status"], "completed")
        ids = [event["id"] for event in body["events"]]
        self.assertEqual(ids, list(range(len(ids))))
        later = client.get(url, params={"after": 1}).json()
        self.assertEqual(later["events"][0]["id"], 2)
        self.assertEqual(client.get(f"/api/sessions/{sid}/turns/nope/progress").status_code, 404)

    def test_follow_up_carries_context(self):
        runner = FakeRunner()
        client = self.client(runner=runner)
        sid = self.session(client)
        client.post(f"/api/sessions/{sid}/turns", json={"question": Q1})
        runner.finish([])
        response = client.post(f"/api/sessions/{sid}/turns", json={"question": "And Q4?"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(Q1, runner.pending[0][1]["question_text"])

    def test_rejections(self):
        client = self.client()
        sid = self.session(client)
        post = lambda body: client.post(f"/api/sessions/{sid}/turns", json=body)  # noqa: E731
        self.assertEqual(post({"question": "  ", "mode": "live"}).status_code, 400)
        self.assertEqual(post({"question": "x" * 4001, "mode": "live"}).status_code, 400)
        self.assertEqual(post({"question": Q1, "mode": "other"}).status_code, 400)
        self.assertEqual(post({"question": Q1, "mode": "replay"}).status_code, 400)
        with mock.patch.dict(os.environ, NO_LIVE_ENV):
            live = post({"question": Q1, "mode": "live"})
        self.assertEqual(live.status_code, 409)
        self.assertIn("not configured", live.json()["detail"])
        self.assertEqual(self.upload(client, sid, name="model.xlsm").status_code, 400)
        self.assertEqual(self.upload(client, sid, data=b"junk").status_code, 400)
        self.assertEqual(client.post("/api/sessions", json={"corpus": "nope"}).status_code, 404)
        self.assertEqual(client.get("/api/sessions/missing").status_code, 404)

    def test_concurrent_turn_rejected(self):
        client = self.client()
        sid = self.session(client)
        first = client.post(f"/api/sessions/{sid}/turns", json={"question": Q1, "mode": "live"})
        second = client.post(f"/api/sessions/{sid}/turns", json={"question": Q1, "mode": "live"})
        self.assertEqual(second.status_code, 409)
        read_events(client, sid, first.json()["turn_id"])

    def test_spend_cap_blocks_live(self):
        with mock.patch.dict(os.environ, LIVE_ENV):
            client = self.client(cap_usd=0.005)
            sid = self.session(client)
            response = client.post(
                f"/api/sessions/{sid}/turns", json={"question": Q1, "mode": "live"}
            )
        self.assertEqual(response.status_code, 409)
        self.assertIn("cap", response.json()["detail"].lower())


class WorkbookFlowTests(AppTestCase):
    def test_workbook_flow_and_export_idempotent(self):
        client = self.client()
        sid = self.session(client)
        before = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        info = self.upload(client, sid).json()
        self.assertEqual(info["snapshot_id"], "a34195a4a257")
        grid = client.get(f"/api/sessions/{sid}/workbook/Model").json()
        self.assertEqual(grid["rows"][6][1]["display"], "1,650.0")
        context = client.put(
            f"/api/sessions/{sid}/context", json={"sheet": "Model", "range": "B7:B8"}
        )
        self.assertEqual(context.json()["cells"], 2)
        too_big = client.put(
            f"/api/sessions/{sid}/context", json={"sheet": "Model", "range": "A1:Z20"}
        )
        self.assertEqual(too_big.status_code, 400)
        _, _, view = self.run_turn(client, sid, Q2)
        self.assertEqual(view["status"], "completed", view)
        self.assertEqual(view["carried"]["workbook_range"], "Model!B7:B8")
        session = client.get(f"/api/sessions/{sid}").json()
        proposal = session["proposals"][0]
        self.assertEqual(proposal["id"], f"{view['id']}-P1")
        self.assertEqual(proposal["status"], "pending")
        self.assertEqual(view["proposal_ids"], [proposal["id"]])
        body = {"snapshot_id": info["snapshot_id"], "proposal_ids": [proposal["id"]]}
        first = client.post(f"/api/sessions/{sid}/exports", json=body)
        second = client.post(f"/api/sessions/{sid}/exports", json=body)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["id"], second.json()["id"])
        download = client.get(first.json()["download_url"])
        self.assertEqual(download.status_code, 200)
        self.assertIn("attachment", download.headers["content-disposition"])
        book = load_workbook(io.BytesIO(download.content))
        self.assertEqual(book["Model"]["B7"].value, 1661.5)
        self.assertIn("Provenance log", book.sheetnames)
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), before)

    def test_reupload_marks_stale(self):
        client = self.client()
        sid = self.session(client)
        self.upload(client, sid)
        _, _, view = self.run_turn(client, sid, Q2)
        self.upload(client, sid)
        session = client.get(f"/api/sessions/{sid}").json()
        self.assertEqual(session["proposals"][0]["status"], "stale")
        self.assertIsNone(session["context"])
        response = client.post(
            f"/api/sessions/{sid}/exports",
            json={"snapshot_id": "a34195a4a257", "proposal_ids": view["proposal_ids"]},
        )
        self.assertEqual(response.status_code, 409)

    def test_demo_workbook_route_removed(self):
        client = self.client()
        sid = self.session(client)
        self.assertEqual(client.post(f"/api/sessions/{sid}/workbook/demo").status_code, 405)

    def test_export_rejects_unknown_ids(self):
        client = self.client()
        sid = self.session(client)
        self.upload(client, sid)
        response = client.post(
            f"/api/sessions/{sid}/exports",
            json={"snapshot_id": "a34195a4a257", "proposal_ids": ["nope"]},
        )
        self.assertEqual(response.status_code, 409)


class FakeRunner:
    """Holds turns open so tests control when they finish."""

    def __init__(self, fail=False):
        self.pending, self.fail = [], fail

    def start(self, job, on_finish=None):
        from provenance.web.worker import Turn

        if self.fail:
            raise RuntimeError("could not start worker")
        turn = Turn(job["turn_id"])
        self.pending.append((turn, job, on_finish))
        return turn

    def finish(
        self,
        proposals,
        *,
        status="completed",
        cost=0.0,
        mode="live_openrouter_langchain",
        documents=None,
    ):
        turn, job, on_finish = self.pending.pop(0)
        turn.result = {
            "report": {
                "run_id": "r",
                "mode": mode,
                "status": status,
                "stop_reason": None if status == "completed" else "model_call_limit",
                "answer": {"answerable": True, "answer": "ok", "claims": []},
                "metrics": {"accounted_cost_usd": cost, "cost_uncertain": False},
                "model": "test/model",
            },
            "proposals": proposals,
            "documents": documents or {},
        }
        on_finish(turn)
        turn.done.set()
        return job


def proposal(cell, value, pid="P1"):
    return {
        "proposal_id": pid,
        "sheet": "Model",
        "cell": cell,
        "new_content": value,
        "rationale": "Align with guidance",
        "citations": [
            {
                "source_id": "cloudflare-q3-2024-release",
                "locator": "L63",
                "quote": "Total revenue of $1,661.0 to $1,662.0 million",
            }
        ],
        "old_display": "1,650.0" if cell == "B7" else "215.0",
        "old_formula": None,
    }


def other_workbook():
    book = load_workbook(FIXTURE)
    book["Model"]["B7"] = 999
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


class MultiTurnWorkbookTests(AppTestCase):
    def start(self, client, sid, question=Q2):
        response = client.post(
            f"/api/sessions/{sid}/turns", json={"question": question, "mode": "live"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["turn_id"]

    def test_proposals_keep_the_snapshot_their_turn_ran_on(self):
        runner = FakeRunner()
        client = self.client(runner=runner)
        sid = self.session(client)
        self.upload(client, sid)
        self.start(client, sid)
        newer = self.upload(client, sid, data=other_workbook(), name="other.xlsx").json()
        runner.finish([proposal("B7", 1661.5)])
        state = client.get(f"/api/sessions/{sid}").json()
        self.assertEqual(state["proposals"][0]["snapshot_id"], "a34195a4a257")
        self.assertEqual(state["proposals"][0]["status"], "stale")
        export = client.post(
            f"/api/sessions/{sid}/exports",
            json={
                "snapshot_id": newer["snapshot_id"],
                "proposal_ids": [state["proposals"][0]["id"]],
            },
        )
        self.assertEqual(export.status_code, 409)

    def test_reproposing_a_cell_supersedes_the_older_proposal(self):
        runner = FakeRunner()
        client = self.client(runner=runner)
        sid = self.session(client)
        self.upload(client, sid)
        self.start(client, sid)
        runner.finish([proposal("B7", 1661.5)])
        self.start(client, sid)
        runner.finish([proposal("B7", 1661.0)])
        proposals = client.get(f"/api/sessions/{sid}").json()["proposals"]
        self.assertEqual([p["status"] for p in proposals], ["superseded", "pending"])
        pending = [p["id"] for p in proposals if p["status"] == "pending"]
        export = client.post(
            f"/api/sessions/{sid}/exports",
            json={"snapshot_id": "a34195a4a257", "proposal_ids": pending},
        )
        self.assertEqual(export.status_code, 200, export.text)

    def test_exports_accumulate_approved_changes(self):
        runner = FakeRunner()
        client = self.client(runner=runner)
        sid = self.session(client)
        self.upload(client, sid)
        self.start(client, sid)
        runner.finish([proposal("B7", 1661.5)])
        first_id = client.get(f"/api/sessions/{sid}").json()["proposals"][0]["id"]
        first = client.post(
            f"/api/sessions/{sid}/exports",
            json={"snapshot_id": "a34195a4a257", "proposal_ids": [first_id]},
        ).json()
        self.start(client, sid)
        runner.finish([proposal("B8", 220.5)])
        second_id = client.get(f"/api/sessions/{sid}").json()["proposals"][1]["id"]
        second = client.post(
            f"/api/sessions/{sid}/exports",
            json={"snapshot_id": "a34195a4a257", "proposal_ids": [second_id]},
        ).json()
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual([c["cell"] for c in second["changes"]], ["Model!B7", "Model!B8"])
        book = load_workbook(io.BytesIO(client.get(second["download_url"]).content))
        self.assertEqual((book["Model"]["B7"].value, book["Model"]["B8"].value), (1661.5, 220.5))
        self.assertEqual(len(client.get(f"/api/sessions/{sid}").json()["exports"]), 2)

    def test_live_proposals_are_labeled_in_the_export(self):
        runner = FakeRunner()
        client = self.client(runner=runner)
        sid = self.session(client)
        self.upload(client, sid)
        self.start(client, sid)
        runner.finish([proposal("B7", 1661.5)])
        state = client.get(f"/api/sessions/{sid}").json()
        self.assertEqual(state["proposals"][0]["mode"], "live_openrouter_langchain")
        export = client.post(
            f"/api/sessions/{sid}/exports",
            json={"snapshot_id": "a34195a4a257", "proposal_ids": [state["proposals"][0]["id"]]},
        ).json()
        book = load_workbook(io.BytesIO(client.get(export["download_url"]).content))
        log = book["Provenance log"]
        headers = [cell.value for cell in log[1]]
        self.assertIn("Generated by", headers)
        self.assertIn("Live model test/model", log.cell(2, headers.index("Generated by") + 1).value)
        self.assertIn("Live model test/model", book["Model"]["B7"].comment.text)

    def test_live_turns_reserve_budget_while_running(self):
        runner = FakeRunner()
        with mock.patch.dict(os.environ, LIVE_ENV):
            client = self.client(runner=runner, cap_usd=0.15)
            first, second = self.session(client), self.session(client)
            ask = lambda sid: client.post(  # noqa: E731
                f"/api/sessions/{sid}/turns", json={"question": "Q?", "mode": "live"}
            )
            self.assertEqual(ask(first).status_code, 200)
            self.assertEqual(runner.pending[0][1]["limits"]["budget_usd"], 0.10)
            self.assertEqual(ask(second).status_code, 200)
            self.assertAlmostEqual(runner.pending[1][1]["limits"]["budget_usd"], 0.05)
            third = self.session(client)
            self.assertEqual(ask(third).status_code, 409)
            runner.finish([], cost=0.004, mode="live_openrouter_langchain")
            self.assertEqual(ask(third).status_code, 200)

    def test_worker_start_failure_releases_the_session(self):
        client = self.client(runner=FakeRunner(fail=True))
        sid = self.session(client)
        response = client.post(f"/api/sessions/{sid}/turns", json={"question": Q1, "mode": "live"})
        self.assertEqual(response.status_code, 500)
        state = client.get(f"/api/sessions/{sid}").json()
        self.assertEqual(state["turns"][0]["status"], "failed")
        retry = client.post(f"/api/sessions/{sid}/turns", json={"question": Q1, "mode": "live"})
        self.assertNotEqual(retry.status_code, 409)

    def test_config_has_no_scripted_starters(self):
        config = self.client().get("/api/config").json()
        self.assertEqual(config["corpora"][0]["scripted"], [])
        self.assertEqual(len(config["corpora"]), 1)


if __name__ == "__main__":
    unittest.main()


class WorkbookWorkspaceTests(AppTestCase):
    def test_bounded_window_beyond_initial_preview_and_context(self):
        book = Workbook()
        book.active.title = "Inputs"
        book.active["AA70"] = 125
        book.active["AB70"] = "=AA70*2"
        book.active["AC75"] = "End"
        data = io.BytesIO()
        book.save(data)
        client = self.client()
        sid = self.session(client)
        uploaded = self.upload(client, sid, data.getvalue(), "synthetic.xlsx").json()
        base = f"/api/sessions/{sid}/workbook/Inputs"
        grid = client.get(base, params={"start_row": 70, "start_col": 27}).json()
        self.assertEqual(grid["snapshot_id"], uploaded["snapshot_id"])
        self.assertEqual((grid["start_row"], grid["start_col"]), (70, 27))
        self.assertEqual(grid["rows"][0][0]["address"], "AA70")
        self.assertEqual(grid["rows"][0][0]["display"], "125")
        self.assertEqual(grid["rows"][0][1]["value_status"], "missing_formula_cache")
        self.assertFalse(grid["rows"][0][1]["editable"])
        self.assertLessEqual(len(grid["rows"]), 60)
        self.assertLessEqual(len(grid["rows"][0]), 26)
        response = client.put(
            f"/api/sessions/{sid}/context", json={"sheet": "Inputs", "range": "AA70:AC75"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cells"], 18)
        for params in ({"start_row": 0}, {"start_col": 16385}, {"start_row": 1048577}):
            self.assertEqual(client.get(base, params=params).status_code, 404)

    def test_export_endpoint_refuses_formula_target_and_new_formula(self):
        for cell, value in (("B9", 0.2), ("B7", "=1+2")):
            with self.subTest(cell=cell):
                runner = FakeRunner()
                client = self.client(runner=runner)
                sid = self.session(client)
                info = self.upload(client, sid).json()
                response = client.post(
                    f"/api/sessions/{sid}/turns", json={"question": Q2, "mode": "live"}
                )
                self.assertEqual(response.status_code, 200)
                runner.finish([proposal(cell, value)])
                state = client.get(f"/api/sessions/{sid}").json()
                result = client.post(
                    f"/api/sessions/{sid}/exports",
                    json={
                        "snapshot_id": info["snapshot_id"],
                        "proposal_ids": [state["proposals"][0]["id"]],
                    },
                )
                self.assertEqual(result.status_code, 409, result.text)
                state = client.get(f"/api/sessions/{sid}").json()
                self.assertEqual(state["exports"], [])
                self.assertEqual(state["proposals"][0]["status"], "pending")
