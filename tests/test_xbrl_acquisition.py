import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eval.scripts.acquire_xbrl_dependencies import acquire

XS = "http://www.w3.org/2001/XMLSchema"


class XbrlAcquisition(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.cache = self.root / "cache"
        self.receipt = self.root / "seed.json"
        self.seed = self.root / "seed.xsd"
        self.output = self.root / "out"

    def prepare(self, children):
        imports = "".join(
            f'<import namespace="{namespace}" schemaLocation="{url}"/>'
            for url, namespace, _ in children
        )
        self.seed.write_text(f'<schema xmlns="{XS}">{imports}</schema>')
        self.receipt.write_text(
            json.dumps(
                {
                    "local_file": "seed.xsd",
                    "response_sha256": hashlib.sha256(self.seed.read_bytes()).hexdigest(),
                    "http_status": 200,
                    "canonical_url": "https://www.sec.gov/Archives/example/seed.xsd",
                    "final_url": "https://ir.odfl.com/sec-filings/all-sec-filings/content/0000950170-25-103916/seed.xsd",
                }
            )
        )
        for url, _, raw in children:
            path = self.cache / url.replace("://", "/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)

    def run_acquisition(self):
        with patch("eval.scripts.acquire_xbrl_dependencies.urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect = AssertionError("No network allowed in fixture")
            return acquire(self.receipt, self.output, self.cache)

    def test_malformed_dependency_retained_and_traversal_continues(self):
        self.prepare(
            [
                ("https://www.xbrl.org/bad.xsd", "urn:bad", b"<broken>"),
                (
                    "https://www.xbrl.org/good.xsd",
                    "urn:good",
                    f'<schema xmlns="{XS}" targetNamespace="urn:good"/>'.encode(),
                ),
            ]
        )
        result = self.run_acquisition()
        self.assertEqual(result["status"], "incomplete_dependency_graph")
        self.assertEqual(
            [d["status"] for d in result["documents"]],
            ["xml_reference_inventory", "failed", "xml_reference_inventory"],
        )
        self.assertIn("ParseError", result["documents"][1]["error"])
        self.assertEqual(json.loads((self.output / "receipt.json").read_text()), result)

    def test_namespace_mismatch_is_incomplete(self):
        self.prepare(
            [
                (
                    "https://www.xbrl.org/wrong.xsd",
                    "urn:wanted",
                    f'<schema xmlns="{XS}" targetNamespace="urn:other"/>'.encode(),
                )
            ]
        )
        result = self.run_acquisition()
        self.assertEqual(result["reference_edges"][0]["status"], "namespace_mismatch")
        self.assertEqual(result["status"], "incomplete_dependency_graph")

    def test_document_limit_preserves_unattempted_edge(self):
        self.prepare([("https://www.xbrl.org/child.xsd", "urn:child", b"<unused/>")])
        with patch("eval.scripts.acquire_xbrl_dependencies.MAX_DOCUMENTS", 1):
            result = self.run_acquisition()
        self.assertEqual(len(result["documents"]), 1)
        self.assertEqual(result["reference_edges"][0]["status"], "document_limit")
        self.assertEqual(result["status"], "incomplete_dependency_graph")

    def test_body_budget_prevents_later_reads(self):
        self.prepare([("https://www.xbrl.org/child.xsd", "urn:child", b"<unused/>")])
        with patch(
            "eval.scripts.acquire_xbrl_dependencies.MAX_TOTAL_BYTES", self.seed.stat().st_size
        ):
            result = self.run_acquisition()
        self.assertEqual(result["documents"][1]["status"], "failed")
        self.assertIn("budget exhausted", result["documents"][1]["error"])
        self.assertEqual(result["observed_body_bytes"], self.seed.stat().st_size)

    def test_partial_budget_bounds_cached_body_with_one_detection_byte(self):
        self.prepare([("https://www.xbrl.org/child.xsd", "urn:child", b"x" * 1000)])
        limit = self.seed.stat().st_size + 3
        with patch("eval.scripts.acquire_xbrl_dependencies.MAX_TOTAL_BYTES", limit):
            result = self.run_acquisition()
        self.assertEqual(result["observed_body_bytes"], limit + 1)
        self.assertEqual(result["documents"][1]["status"], "failed")
        self.assertIn("Byte limit exceeded", result["documents"][1]["error"])

    def test_conflicting_delivery_routes_are_not_silently_aliased(self):
        self.prepare([])
        self.seed.write_text(
            f'<schema xmlns="{XS}"><import schemaLocation="child.xsd"/>'
            '<include schemaLocation="https://www.sec.gov/Archives/example/child.xsd"/></schema>'
        )
        receipt = json.loads(self.receipt.read_text())
        receipt["response_sha256"] = hashlib.sha256(self.seed.read_bytes()).hexdigest()
        self.receipt.write_text(json.dumps(receipt))
        cached = (
            self.cache
            / "https/ir.odfl.com/sec-filings/all-sec-filings/content/0000950170-25-103916/child.xsd"
        )
        cached.parent.mkdir(parents=True)
        cached.write_text(f'<schema xmlns="{XS}"/>')
        result = self.run_acquisition()
        self.assertEqual(result["reference_edges"][1]["status"], "conflicting_delivery_route")
        self.assertEqual(result["status"], "incomplete_dependency_graph")

    def test_code_change_prevents_success_publication(self):
        self.prepare([])
        original = Path.read_bytes
        counts = {}

        def changed(path):
            raw = original(path)
            if path.name == "acquire_xbrl_dependencies.py":
                counts[path] = counts.get(path, 0) + 1
                if counts[path] > 1:
                    return raw + b" "
            return raw

        with (
            patch.object(Path, "read_bytes", changed),
            self.assertRaisesRegex(ValueError, "Driver or parser changed"),
        ):
            self.run_acquisition()
        self.assertNotEqual(
            json.loads((self.output / "receipt.json").read_text())["status"],
            "reference_graph_acquired",
        )


if __name__ == "__main__":
    unittest.main()
