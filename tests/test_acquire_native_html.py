import hashlib
import io
import json
import tempfile
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest import mock

from eval.scripts.acquire_native_html import acquire, identity


def content(document, period=None):
    return (
        f'<html><ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric>'
        f'<ix:nonNumeric name="dei:DocumentPeriodEndDate">{period or document["period_end"]}</ix:nonNumeric>'
        f'<ix:nonNumeric name="dei:EntityCentralIndexKey">{document["cik"]}</ix:nonNumeric></html>'
    ).encode()


class Response(io.BytesIO):
    status = 200

    def __init__(self, body, url):
        super().__init__(body)
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = "text/html"
        self.headers["Content-Length"] = str(len(body))

    def geturl(self):
        return self.url


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.selection = self.root / "selection.json"
        self.documents = []
        for i in range(6):
            cik = f"{i // 2 + 1:010d}"
            accession = f"{cik}-25-{i + 1:06d}"
            self.documents.append(
                {
                    "source_id": f"source-{i}",
                    "issuer_id": f"issuer-{i // 2}",
                    "cik": cik,
                    "accession": accession,
                    "form": "10-Q",
                    "period_end": "2025-06-30",
                    "index_reported_bytes": 1,
                    "primary_url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/filing.htm",
                }
            )
        self.selection.write_text(json.dumps({"documents": self.documents}))
        self.sha = hashlib.sha256(self.selection.read_bytes()).hexdigest()

    def test_identity_rejects_challenge_and_wrong_period_and_supports_display_date(self):
        document = self.documents[0]
        with self.assertRaisesRegex(ValueError, "does not establish"):
            identity(b"<html>Access denied</html>", document)
        with self.assertRaisesRegex(ValueError, "does not establish"):
            identity(content(document, "2024-06-30"), document)
        self.assertIn(
            "10-Q", identity(content(document, "June 30, 2025"), document)["dei:documenttype"]
        )
        contradictory = content(document) + (
            b'<ix:nonNumeric name="dei:DocumentType">10-K</ix:nonNumeric>'
            b'<ix:nonNumeric name="dei:DocumentPeriodEndDate">2024-12-31</ix:nonNumeric>'
        )
        with self.assertRaisesRegex(ValueError, "does not establish"):
            identity(contradictory, document)
        wrong = dict(document, cik="0000000999")
        with self.assertRaisesRegex(ValueError, "does not establish"):
            identity(content(wrong), document)

    def test_success_and_failure_receipts_preserve_selected_denominator(self):
        def open_response(request, timeout):
            document = next(d for d in self.documents if d["primary_url"] == request.full_url)
            if document["source_id"] == "source-1":
                raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)
            if document["source_id"] == "source-2":
                return Response(b"<html>Access denied</html>", request.full_url)
            return Response(content(document), request.full_url)

        opener = mock.Mock()
        opener.open.side_effect = open_response
        output = self.root / "acquired"
        with (
            mock.patch("urllib.request.build_opener", return_value=opener),
            mock.patch("time.sleep"),
        ):
            report = acquire(self.selection, self.sha, output)
        self.assertEqual(report["document_denominator"], 6)
        self.assertEqual(report["identity_verified_count"], 4)
        self.assertEqual(opener.open.call_count, 6)
        self.assertEqual(report["documents"][1]["http_status"], 403)
        self.assertEqual(report["documents"][2]["status"], "failed")
        self.assertTrue((output / "source-2.partial").exists())
        self.assertFalse((output / "source-2.html").exists())
        self.assertFalse(report["documents"][0]["index_size_matches"])
        with self.assertRaises(FileExistsError):
            acquire(self.selection, self.sha, output)

    def test_interrupted_request_keeps_pending_sources_and_byte_limit_fails(self):
        opener = mock.Mock()
        opener.open.side_effect = KeyboardInterrupt()
        output = self.root / "interrupted"
        with mock.patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(KeyboardInterrupt):
                acquire(self.selection, self.sha, output)
        report = json.loads((output / "acquisition.json").read_text())
        self.assertEqual(
            [d["status"] for d in report["documents"]], ["interrupted"] + ["pending"] * 5
        )
        opener.open.side_effect = lambda request, timeout: Response(b"x" * 20, request.full_url)
        with (
            mock.patch("urllib.request.build_opener", return_value=opener),
            mock.patch("time.sleep"),
            mock.patch("eval.scripts.acquire_native_html.MAX_BYTES", 10),
        ):
            report = acquire(self.selection, self.sha, self.root / "oversize")
        self.assertEqual(report["identity_verified_count"], 0)
        self.assertTrue(all(d["partial_bytes"] == 11 for d in report["documents"]))


if __name__ == "__main__":
    unittest.main()
