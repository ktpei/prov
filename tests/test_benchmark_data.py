"""Pinned acquisition fails closed before publishing unverified bytes."""

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from provenance.benchmark_data import fetch, read_records


class AcquisitionTests(unittest.TestCase):
    def test_verified_download_and_immutable_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = b'[{"id":"synthetic"}]'
            source = {
                "filename": "data.json",
                "url": "https://example.org/pinned/data.json",
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps({"sources": {"test": source}}))
            with patch("urllib.request.urlopen", return_value=io.BytesIO(raw)):
                self.assertEqual(fetch("test", root / "data", catalog=catalog), source)
            self.assertEqual(read_records(root / "data/data.json"), [{"id": "synthetic"}])
            with self.assertRaises(FileExistsError), patch("urllib.request.urlopen") as request:
                fetch("test", root / "data", catalog=catalog)
            request.assert_not_called()

    def test_changed_bytes_and_bad_filename_never_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = {
                "filename": "data.json",
                "url": "https://example.org/data",
                "sha256": "0" * 64,
            }
            catalog = root / "catalog.json"
            for filename in ("data.json", "../escape.json"):
                source["filename"] = filename
                catalog.write_text(json.dumps({"sources": {"test": source}}))
                with (
                    patch("urllib.request.urlopen", return_value=io.BytesIO(b"changed")),
                    self.assertRaises(ValueError),
                ):
                    fetch("test", root / "data", catalog=catalog)
                self.assertFalse((root / "data").exists())


if __name__ == "__main__":
    unittest.main()
