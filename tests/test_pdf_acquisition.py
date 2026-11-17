import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest import mock

from eval.scripts.table_assessment_run import runtime_digest
from provenance.evidence_coverage import digest

PATH = Path(__file__).resolve().parents[1] / "eval/assessments/financebench-context-v1/acquire.py"
spec = importlib.util.spec_from_file_location("pdf_acquisition", PATH)
acquisition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acquisition)


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


class Response(io.BytesIO):
    def __init__(self, url, body, encoding="identity"):
        super().__init__(body)
        self.status = 200
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = "application/pdf"
        self.headers["Content-Encoding"] = encoding
        self.headers["Content-Length"] = str(len(body))

    def geturl(self):
        return self.url


class PDFAcquisitionTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        metadata = root / "metadata"
        metadata.mkdir()
        revision = "a" * 40
        body = b"%PDF-synthetic fixture\n"
        selected, sources, entries = [], [], []
        for i in range(6):
            name = f"D{i}"
            entry = {
                "path": f"pdfs/{name}.pdf",
                "type": "blob",
                "mode": "100644",
                "size": len(body),
                "sha": acquisition.blob_sha(body),
            }
            url = f"https://raw.githubusercontent.com/patronus-ai/financebench/{revision}/pdfs/{name}.pdf"
            selected.append(
                {"doc_name": name, "task_id": f"q{i}", "doc_link": f"https://example.org/{name}"}
            )
            sources.append(
                {
                    "doc_name": name,
                    "task_id": f"q{i}",
                    "original_metadata_url": selected[-1]["doc_link"],
                    "download_url": url,
                    "tree_entry": entry,
                }
            )
            entries.append(entry)
        write(
            root / "selection.json",
            {
                "version": "financebench-context-selection-v1",
                "revision": revision,
                "selected": selected,
            },
        )
        write(metadata / "commit.json", {"sha": revision, "tree": {"sha": "b" * 40}})
        write(metadata / "tree.json", {"sha": "b" * 40, "truncated": False, "tree": entries})
        write(
            root / "inventory.json",
            {
                "version": "financebench-context-pdf-inventory-v1",
                "selection_sha256": digest(root / "selection.json"),
                "revision": revision,
                "tree_sha": "b" * 40,
                "sources": sources,
                "commit_response_sha256": digest(metadata / "commit.json"),
                "tree_response_sha256": digest(metadata / "tree.json"),
            },
        )
        (root / "acquisition-plan.md").write_bytes(
            (PATH.parent / "acquisition-plan.md").read_bytes()
        )
        protocol = root / "protocol.json"
        write(
            protocol,
            {
                "version": "financebench-pdf-acquisition-v1",
                "script_sha256": digest(PATH),
                "plan_sha256": digest(root / "acquisition-plan.md"),
                "runtime_sha256": runtime_digest(),
                "selection_sha256": digest(root / "selection.json"),
                "inventory_sha256": digest(root / "inventory.json"),
                "max_bytes": acquisition.MAX_BYTES,
                "socket_timeout_seconds": 20,
                "elapsed_check_seconds": 120,
            },
        )
        return root, metadata, protocol, root / "output", sources, body

    def test_exact_blob_bytes_and_full_denominator(self):
        root, metadata, protocol, output, sources, body = self.fixture()
        opener = mock.Mock()
        opener.open.side_effect = [Response(s["download_url"], body) for s in sources]
        with (
            mock.patch.multiple(acquisition, HERE=root, METADATA=metadata),
            mock.patch.object(acquisition.urllib.request, "build_opener", return_value=opener),
        ):
            result = acquisition.acquire(protocol, output)
        self.assertEqual(opener.open.call_count, 6)
        self.assertEqual(result["verified_count"], 6)
        self.assertEqual(result["selected_denominator"], 6)
        self.assertEqual(result["documents"][0]["sha256"], hashlib.sha256(body).hexdigest())
        self.assertNotEqual(acquisition.blob_sha(body), hashlib.sha1(body).hexdigest())
        for call in opener.open.call_args_list:
            self.assertEqual(call.kwargs["timeout"], 20)
            self.assertEqual(call.args[0].get_header("Accept-encoding"), "identity")

    def test_failures_keep_slots_no_retries_and_bound_partial_bytes(self):
        root, metadata, protocol, output, sources, body = self.fixture()
        opener = mock.Mock()
        opener.open.side_effect = [
            Response(sources[0]["download_url"], body[:-1] + b"x"),
            Response(sources[1]["download_url"], body + b"overflow"),
            urllib.error.HTTPError(sources[2]["download_url"], 403, "Forbidden", {}, None),
            *[Response(s["download_url"], body) for s in sources[3:]],
        ]
        with (
            mock.patch.multiple(acquisition, HERE=root, METADATA=metadata),
            mock.patch.object(acquisition.urllib.request, "build_opener", return_value=opener),
        ):
            result = acquisition.acquire(protocol, output)
        self.assertEqual(opener.open.call_count, 6)
        self.assertEqual(result["verified_count"], 3)
        self.assertEqual(
            [d["status"] for d in result["documents"]], ["failed"] * 3 + ["verified_blob"] * 3
        )
        self.assertEqual(result["documents"][1]["partial_bytes"], len(body) + 1)
        self.assertEqual(result["documents"][2]["http_status"], 403)

    def test_route_validation_precedes_any_request(self):
        root, metadata, protocol, output, sources, body = self.fixture()
        inventory = json.loads((root / "inventory.json").read_text())
        inventory["sources"][-1]["download_url"] = "https://example.org/other"
        write(root / "inventory.json", inventory)
        policy = json.loads(protocol.read_text())
        policy["inventory_sha256"] = digest(root / "inventory.json")
        write(protocol, policy)
        with (
            mock.patch.multiple(acquisition, HERE=root, METADATA=metadata),
            mock.patch.object(acquisition.urllib.request, "build_opener") as opener,
        ):
            with self.assertRaisesRegex(ValueError, "mirror identity"):
                acquisition.acquire(protocol, output)
            opener.assert_not_called()
        self.assertFalse(output.exists())

    def test_interruption_retains_partial_and_pending_slots(self):
        root, metadata, protocol, output, sources, body = self.fixture()
        response = Response(sources[0]["download_url"], body)
        response.read1 = mock.Mock(side_effect=[body[:2], KeyboardInterrupt])
        opener = mock.Mock()
        opener.open.return_value = response
        with (
            mock.patch.multiple(acquisition, HERE=root, METADATA=metadata),
            mock.patch.object(acquisition.urllib.request, "build_opener", return_value=opener),
        ):
            with self.assertRaises(KeyboardInterrupt):
                acquisition.acquire(protocol, output)
        result = json.loads((output / "acquisition.json").read_text())
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(result["documents"][0]["partial_bytes"], 2)
        self.assertEqual([d["status"] for d in result["documents"]][1:], ["pending"] * 5)
        self.assertEqual(opener.open.call_count, 1)

    def test_input_and_downloaded_body_mutations_invalidate_run(self):
        for mutation in ["input", "body"]:
            root, metadata, protocol, output, sources, body = self.fixture()
            calls = 0

            def open_response(
                request, timeout, mutation=mutation, body=body, root=root, output=output
            ):
                nonlocal calls
                calls += 1
                if mutation == "input":
                    path = root / "selection.json"
                    path.write_bytes(path.read_bytes() + b"\n")
                elif calls == 2:
                    (output / "D0.pdf").write_bytes(b"tampered")
                return Response(request.full_url, body)

            opener = mock.Mock()
            opener.open.side_effect = open_response
            with (
                mock.patch.multiple(acquisition, HERE=root, METADATA=metadata),
                mock.patch.object(acquisition.urllib.request, "build_opener", return_value=opener),
            ):
                with self.assertRaisesRegex(ValueError, "identity|artifact changed"):
                    acquisition.acquire(protocol, output)
            self.assertEqual(
                json.loads((output / "acquisition.json").read_text())["status"], "invalidated"
            )
            self.assertEqual(calls, 1 if mutation == "input" else 6)
