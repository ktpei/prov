import hashlib
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from eval.scripts.capture_submissions import capture
from tests.test_acquire_native_html import Response


class SubmissionCaptureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.selection = self.root / "selection.json"
        self.candidates = self.root / "candidates.json"
        documents = []
        for i in range(6):
            accession = f"0000000001-25-{i:06d}"
            base = f"https://www.sec.gov/Archives/edgar/data/1/{accession.replace('-', '')}"
            documents.append(
                {
                    "source_id": f"source-{i}",
                    "cik": "0000000001",
                    "accession": accession,
                    "period_end": "2025-06-30",
                    "form": "10-Q",
                    "index_url": base + "/" + accession + "-index.htm",
                    "primary_url": base + "/filing.htm",
                }
            )
        self.selection.write_text(json.dumps({"documents": documents}))
        self.selection_hash = hashlib.sha256(self.selection.read_bytes()).hexdigest()
        self.record = {
            "selection_sha256": self.selection_hash,
            "sources": [
                {
                    **{
                        k: d[k]
                        for k in ["source_id", "cik", "accession", "period_end", "index_url"]
                    },
                    "complete_submission_url": d["primary_url"].rsplit("/", 1)[0]
                    + "/"
                    + d["accession"]
                    + ".txt",
                    "expected_document_type": "10-Q",
                    "expected_sequence": 1,
                    "expected_filename": "filing.htm",
                }
                for d in documents[:4]
            ],
        }

    def run_capture(self, name="out"):
        self.candidates.write_text(json.dumps(self.record))
        return capture(
            self.selection,
            self.candidates,
            self.selection_hash,
            hashlib.sha256(self.candidates.read_bytes()).hexdigest(),
            self.root / name,
        )

    def response(self, request, timeout):
        response = Response(b"unverified container bytes", request.full_url)
        response.headers.replace_header("Content-Type", "text/plain")
        return response

    def test_capture_never_promotes_containers_and_retains_six_sources(self):
        def response(request, timeout):
            if "000001.txt" in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)
            return self.response(request, timeout)

        with mock.patch("urllib.request.build_opener") as opener, mock.patch("time.sleep"):
            opener.return_value.open.side_effect = response
            result = self.run_capture()
            self.assertEqual(opener.return_value.open.call_count, 4)
            self.assertEqual(len(result["documents"]), 6)
            self.assertEqual(result["identity_verified_count"], 0)
            self.assertEqual(result["captured_unverified_count"], 3)
            self.assertEqual(result["documents"][1]["http_status"], 403)
            self.assertEqual(result["documents"][4]["status"], "not_requested_no_candidate")
            with self.assertRaises(FileExistsError):
                self.run_capture()
            self.assertEqual(opener.return_value.open.call_count, 4)

    def test_invalid_route_or_member_metadata_rejected_before_requests(self):
        for key, value in [
            ("complete_submission_url", "https://example.com/file.txt"),
            ("expected_sequence", True),
            ("expected_filename", "other.htm"),
        ]:
            original = self.record["sources"][0][key]
            self.record["sources"][0][key] = value
            with mock.patch("urllib.request.build_opener") as opener, self.assertRaises(ValueError):
                self.run_capture()
            opener.assert_not_called()
            self.record["sources"][0][key] = original

    def test_oversized_or_wrong_media_responses_fail_without_promotion(self):
        with (
            mock.patch("urllib.request.build_opener") as opener,
            mock.patch("time.sleep"),
            mock.patch("eval.scripts.capture_submissions.MAX_BYTES", 8),
        ):
            opener.return_value.open.side_effect = self.response
            result = self.run_capture()
            self.assertEqual(result["captured_unverified_count"], 0)
            self.assertEqual(result["documents"][0]["partial_bytes"], 9)
        with mock.patch("urllib.request.build_opener") as opener, mock.patch("time.sleep"):
            opener.return_value.open.side_effect = lambda request, timeout: Response(
                b"challenge", request.full_url
            )
            result = self.run_capture("media")
            self.assertEqual(result["captured_unverified_count"], 0)

    def test_interruption_retains_pending_dispositions(self):
        with mock.patch("urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect = KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt):
                self.run_capture()
        report = json.loads((self.root / "out" / "acquisition.json").read_text())
        self.assertEqual(report["documents"][0]["status"], "interrupted")
        self.assertEqual(report["documents"][1]["status"], "pending")
        self.assertEqual(report["documents"][5]["status"], "not_requested_no_candidate")

    def test_deadline_length_and_redirect_mismatch_do_not_capture(self):
        def incorrect(request, timeout):
            response = self.response(request, timeout)
            response.headers.replace_header("Content-Length", "9999")
            return response

        with mock.patch("urllib.request.build_opener") as opener, mock.patch("time.sleep"):
            opener.return_value.open.side_effect = incorrect
            result = self.run_capture("length")
            self.assertEqual(result["captured_unverified_count"], 0)
            self.assertTrue(result["documents"][0]["eof_observed"])
            self.assertIn("partial_sha256", result["documents"][0])
        with (
            mock.patch("urllib.request.build_opener") as opener,
            mock.patch("time.sleep"),
            mock.patch("eval.scripts.capture_submissions.ELAPSED_LIMIT_SECONDS", -1),
        ):
            opener.return_value.open.side_effect = self.response
            result = self.run_capture("deadline")
            self.assertEqual(result["captured_unverified_count"], 0)
            self.assertIn("TimeoutError", result["documents"][0]["error"])

        def redirected(request, timeout):
            response = self.response(request, timeout)
            response.url = "https://example.com/other"
            return response

        with mock.patch("urllib.request.build_opener") as opener, mock.patch("time.sleep"):
            opener.return_value.open.side_effect = redirected
            self.assertEqual(self.run_capture("redirect")["captured_unverified_count"], 0)
