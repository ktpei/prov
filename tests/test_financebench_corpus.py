"""Document-only corpus assembly binds metadata and excludes evaluator gold."""

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter

from provenance.benchmarks import prepare
from provenance.financebench_corpus import build_corpus
from provenance.sources import Sources


def prepared():
    task = {
        "id": "synthetic",
        "dataset": "financebench",
        "subset": "open_source",
        "source_split": "public",
        "question": "Synthetic question?",
        "context": {},
        "metadata": {"doc_name": "SYN_2024_10K"},
        "reference": {
            "answer": "GOLD_SENTINEL",
            "metric": "financebench_semantic_review",
            "evidence": [],
        },
    }
    source = {
        "dataset": "financebench",
        "subset": "open_source",
        "source_split": "public",
        "url": "https://example.org",
        "revision": "a" * 40,
        "sha256": "b" * 64,
        "license": "synthetic",
    }
    return prepare(
        [task],
        source=source,
        count=1,
        seed=17,
        condition="full_agent",
        development_groups=["SYN_2024_10K"],
    )


class FinanceBenchCorpusTests(unittest.TestCase):
    def metadata(self, root):
        path, source = root / "metadata.jsonl", root / "source.json"
        raw = json.dumps(
            {
                "doc_name": "SYN_2024_10K",
                "company": "Synthetic",
                "doc_period": 2024,
                "doc_type": "10K",
                "doc_link": "https://example.org/report.pdf",
            }
        ).encode()
        path.write_bytes(raw)
        source.write_text(
            json.dumps(
                {
                    "dataset": "financebench_documents",
                    "revision": "a" * 40,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
        )
        return path, source

    def test_full_originals_are_verified_without_ingesting_gold(self):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        buffer = io.BytesIO()
        writer.write(buffer)
        raw = buffer.getvalue()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata, source = self.metadata(root)
            with patch("urllib.request.urlopen", return_value=io.BytesIO(raw)) as request:
                binding = build_corpus(prepared(), metadata, source, root / "corpus")
            self.assertIn(
                "/" + "a" * 40 + "/pdfs/SYN_2024_10K.pdf", request.call_args.args[0].full_url
            )
            self.assertEqual(
                binding["original_hashes"]["SYN_2024_10K"], hashlib.sha256(raw).hexdigest()
            )
            corpus = Sources(root / "corpus")
            self.assertNotIn("GOLD_SENTINEL", str(corpus.documents))
            self.assertEqual(set(corpus.documents), {"SYN_2024_10K"})
            self.assertIsNone(corpus.documents["SYN_2024_10K"]["published"])
            with patch("urllib.request.urlopen") as request, self.assertRaises(FileExistsError):
                build_corpus(prepared(), metadata, source, root / "corpus")
            request.assert_not_called()

    def test_conflicting_selected_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata, source = self.metadata(root)
            row = json.loads(metadata.read_text())
            other = dict(row, doc_period=2023)
            metadata.write_text(json.dumps(row) + "\n" + json.dumps(other) + "\n")
            identity = json.loads(source.read_text())
            identity["sha256"] = hashlib.sha256(metadata.read_bytes()).hexdigest()
            source.write_text(json.dumps(identity))
            with (
                patch("urllib.request.urlopen") as request,
                self.assertRaisesRegex(ValueError, "Conflicting"),
            ):
                build_corpus(prepared(), metadata, source, root / "corpus")
            request.assert_not_called()

    def test_metadata_tampering_rejected_before_download_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata, source = self.metadata(root)
            metadata.write_text("changed")
            with (
                patch("urllib.request.urlopen") as request,
                self.assertRaisesRegex(ValueError, "identity"),
            ):
                build_corpus(prepared(), metadata, source, root / "corpus")
            request.assert_not_called()
            self.assertFalse((root / "corpus").exists())


if __name__ == "__main__":
    unittest.main()
