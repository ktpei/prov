"""Host receipt and typed live-Excel apply plans; no live provider or Office calls."""

import io

from openpyxl import Workbook

from tests.test_web_app import AppTestCase, FakeRunner, proposal


class ExcelApplyTests(AppTestCase):
    def setup_proposal(self, client, runner, old=0.0375, cell="J36"):
        book = Workbook()
        book.active.title = "Model"
        book.active["J36"] = old
        book.active["J22"] = "=J36"
        buffer = io.BytesIO()
        book.save(buffer)
        sid = self.session(client)
        info = self.upload(client, sid, buffer.getvalue(), "model.xlsx").json()
        response = client.post(
            f"/api/sessions/{sid}/turns",
            json={"question": "Set the growth assumption to 4%", "mode": "live"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        runner.finish([proposal(cell, 0.04)])
        state = client.get(f"/api/sessions/{sid}").json()
        body = {"snapshot_id": info["snapshot_id"], "proposal_ids": [state["proposals"][0]["id"]]}
        return sid, body

    def test_typed_plan_and_separate_applied_receipt(self):
        runner = FakeRunner()
        with self.client(runner=runner) as client:
            sid, body = self.setup_proposal(client, runner)
            url = f"/api/sessions/{sid}/excel"
            plan = client.post(f"{url}/apply-plan", json=body)
            self.assertEqual(plan.status_code, 200, plan.text)
            self.assertEqual(plan.json()["edits"][0]["old_content"], 0.0375)
            self.assertEqual(plan.json()["edits"][0]["new_content"], 0.04)
            self.assertEqual(
                client.get(f"/api/sessions/{sid}").json()["proposals"][0]["status"], "pending"
            )
            response = client.post(f"{url}/applied", json=body)
            self.assertEqual(response.json()["verification"], "excel_client_readback")
            self.assertEqual(
                client.get(f"/api/sessions/{sid}").json()["proposals"][0]["status"], "applied"
            )
            self.assertEqual(client.post(f"{url}/apply-plan", json=body).status_code, 409)

    def test_snapshot_and_proposal_ids_must_match(self):
        runner = FakeRunner()
        with self.client(runner=runner) as client:
            sid, body = self.setup_proposal(client, runner)
            for invalid in (
                {**body, "snapshot_id": "other"},
                {**body, "proposal_ids": []},
                {**body, "proposal_ids": ["missing"]},
                {**body, "proposal_ids": body["proposal_ids"] * 2},
            ):
                for route in ("apply-plan", "applied"):
                    response = client.post(f"/api/sessions/{sid}/excel/{route}", json=invalid)
                    self.assertEqual(response.status_code, 409, response.text)

    def test_formula_and_error_targets_are_rejected(self):
        for old, target in ((0.0375, "J22"), ("#DIV/0!", "J36")):
            with self.subTest(target=target):
                runner = FakeRunner()
                with self.client(runner=runner) as client:
                    sid, body = self.setup_proposal(client, runner, old, target)
                    response = client.post(f"/api/sessions/{sid}/excel/apply-plan", json=body)
                    self.assertEqual(response.status_code, 409, response.text)

    def test_numeric_looking_text_keeps_its_type(self):
        runner = FakeRunner()
        with self.client(runner=runner) as client:
            sid, body = self.setup_proposal(client, runner, "0.0375")
            response = client.post(f"/api/sessions/{sid}/excel/apply-plan", json=body)
            self.assertEqual(response.json()["edits"][0]["old_content"], "0.0375")
