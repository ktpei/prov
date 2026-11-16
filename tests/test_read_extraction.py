import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from provenance.sources import Sources


class ReadExtractionTests(unittest.TestCase):
    def corpus(self, lines=None, extraction=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        text = (
            "\n".join(
                lines
                or [
                    "Revenue 10",
                    "Costs 5",
                    "Inventory 3",
                    "Assets 20",
                    "Notes",
                    "[No native text extracted]",
                ]
            )
            + "\n"
        )
        (root / "text.txt").write_text(text)
        (root / "original.pdf").write_bytes(b"synthetic original")
        diagnostics = {
            "parser": "pypdf-layout",
            "diagnostics_version": "pdf-extraction-diagnostics-v2",
            "page_count": 4,
            "package_versions": {"pypdf": "synthetic", "fonttools": None},
            "warning_count": 7,
            "warning_samples": [{"page": 4, "message": "missing font", "count": 3}],
            "warning_samples_truncated": True,
            "empty_native_text_pages": [4],
            "text_completeness": "not_verified",
            "ocr_performed": False,
            "warnings": ["Geometry unverified", "Page 4 has no native text"],
            "pages": [
                {
                    "page": n,
                    "native_line_count": 0 if n == 4 else 2,
                    "native_nonwhitespace_characters": 0 if n == 4 else 20,
                    "emitted_line_start": start,
                    "emitted_line_end": end,
                    "warning_count": 7 if n == 4 else 0,
                }
                for n, start, end in [(1, 1, 2), (2, 3, 4), (3, 5, 5), (4, 6, 6)]
            ],
        }
        source = {
            "id": "s",
            "title": "Synthetic",
            "text_file": "text.txt",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "original_file": "original.pdf",
            "original_sha256": hashlib.sha256(b"synthetic original").hexdigest(),
            "line_locations": [{"page": n} for n in [1, 1, 2, 2, 3, 4]],
            "extraction": diagnostics if extraction is None else extraction,
        }
        (root / "sources.json").write_text(json.dumps({"sources": [source]}))
        return root

    def test_default_and_explicit_full_are_byte_compatible_and_optin_changes_only_metadata(self):
        root = self.corpus()
        default = Sources(root)
        full = Sources(root, read_extraction_version="full-v1")
        compact = Sources(root, read_extraction_version="pdf-returned-pages-v1")
        self.assertEqual(default.search("Revenue", 1), compact.search("Revenue", 1))
        a, b, c = [s.read("s", 1, 2, 1) for s in [default, full, compact]]
        self.assertEqual(json.dumps(a), json.dumps(b))
        self.assertEqual(
            {k: v for k, v in a.items() if k != "extraction"},
            {k: v for k, v in c.items() if k != "extraction"},
        )
        self.assertEqual(default.seen, compact.seen)
        self.assertEqual(c["extraction"]["pages"], a["extraction"]["pages"][:1])
        with self.assertRaisesRegex(ValueError, "Unknown read extraction"):
            Sources(root, read_extraction_version="unrecognized")

    def test_full_warnings_and_counts_survive_multpage_projection_with_full_hash(self):
        root = self.corpus()
        source = Sources(root, read_extraction_version="pdf-returned-pages-v1")
        original = copy.deepcopy(source.documents["s"]["extraction"])
        response = source.read("s", 2, 3, 1)["extraction"]
        self.assertEqual([p["page"] for p in response["pages"]], [1, 2])
        for k, v in original.items():
            if k != "pages":
                self.assertEqual(response[k], v)
        projection = response["read_projection"]
        self.assertEqual(projection["retained_page_count"], 2)
        self.assertEqual(projection["omitted_page_count"], 2)
        self.assertEqual(response["page_count"], 4)
        expected = hashlib.sha256(
            json.dumps(original, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
        ).hexdigest()
        self.assertEqual(projection["full_diagnostics_sha256"], expected)
        self.assertEqual(
            projection["full_diagnostics_location"],
            {"manifest": "sources.json", "source_id": "s", "field": "extraction"},
        )
        self.assertEqual(source.documents["s"]["extraction"], original)
        response["pages"][0]["native_line_count"] = 999
        response["warning_samples"][0]["message"] = "mutated"
        self.assertEqual(source.documents["s"]["extraction"], original)
        self.assertEqual(source.read("s", 2, 3, 1)["extraction"]["pages"][0], original["pages"][0])
        source.documents["s"]["extraction"]["pages"][-1]["warning_count"] += 1
        self.assertNotEqual(
            source.read("s", 2, 3, 1)["extraction"]["read_projection"]["full_diagnostics_sha256"],
            expected,
        )

    def test_truncation_selects_only_actually_returned_pages(self):
        root = self.corpus(["x" * 9000, "y" * 9000, "z" * 1000, "more", "notes", "empty marker"])
        source = Sources(root, read_extraction_version="pdf-returned-pages-v1")
        response = source.read("s", 1, 6, 1)
        self.assertEqual(response["locator"], "L1-L2")
        self.assertEqual(response["next_start_line"], 3)
        self.assertEqual([p["page"] for p in response["extraction"]["pages"]], [1])
        self.assertEqual(response["extraction"]["read_projection"]["omitted_page_count"], 3)
        self.assertEqual(response["extraction"]["warning_count"], 7)
        self.assertEqual(response["extraction"]["empty_native_text_pages"], [4])
        self.assertEqual(response["extraction"]["pages"][0]["emitted_line_end"], 2)

    def test_malformed_page_records_or_mappings_fail_without_marking_lines_seen(self):
        root = self.corpus()
        original = Sources(root).documents["s"]
        changes = [
            lambda d: d["extraction"]["pages"][1].update(page=1),
            lambda d: d["extraction"]["pages"][0].update(page=True),
            lambda d: d["extraction"]["pages"].pop(),
            lambda d: d["extraction"].update(page_count=True),
            lambda d: d["extraction"].update(read_projection={}),
            lambda d: d["line_locations"][0].update(page=True),
            lambda d: d["line_locations"][0].update(page=5),
            lambda d: d.update(line_locations=[]),
            lambda d: d.update(line_locations=None),
            lambda d: d.update(line_locations={}),
            lambda d: d["line_locations"][0].update(page=2),
            lambda d: d["extraction"]["pages"][0].pop("emitted_line_start"),
            lambda d: d["extraction"]["pages"][0].update(emitted_line_end=True),
            lambda d: d["extraction"]["pages"][0].update(emitted_line_end=999),
        ]
        for change in changes:
            with self.subTest(change=change):
                source = Sources(root, read_extraction_version="pdf-returned-pages-v1")
                source.documents["s"] = copy.deepcopy(original)
                change(source.documents["s"])
                with self.assertRaisesRegex(ValueError, "Compact PDF diagnostics"):
                    source.read("s", 1, 2, 1)
                self.assertEqual(source.seen, {})
                result = source.call(
                    "read_source", {"source_id": "s", "start_line": 1, "end_line": 2}, 1
                )
                self.assertIn("error", result)
                self.assertEqual(source.seen, {})

    def test_legacy_html_and_unknown_metadata_are_preserved(self):
        for metadata in [
            {"parser": "stdlib-html-v1", "warnings": ["geometry missing"]},
            {"parser": "pypdf-layout", "page_count": 4},
            {"diagnostics_version": "future-v3", "pages": ["opaque"]},
        ]:
            with self.subTest(metadata=metadata):
                root = self.corpus(extraction=metadata)
                full = Sources(root).read("s", 1, 2, 1)
                compact = Sources(root, read_extraction_version="pdf-returned-pages-v1").read(
                    "s", 1, 2, 1
                )
                self.assertEqual(json.dumps(full), json.dumps(compact))


if __name__ == "__main__":
    unittest.main()
