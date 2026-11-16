import copy
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from provenance.xbrl_facts import checked_boundary, typed_value, verified_occurrences


class TypedXbrlValues(unittest.TestCase):
    def test_exact_numbers_and_signed_zero(self):
        for lexical in ("123.4500", "-0.00", "123456789012345678901234567890.12345", "1E+30"):
            self.assertEqual(typed_value(Decimal(lexical)), {"kind": "decimal", "value": lexical})
        self.assertEqual(typed_value(2**64), {"kind": "integer", "value": str(2**64)})

    def test_boolean_is_not_an_integer(self):
        self.assertEqual(typed_value(True), {"kind": "boolean", "value": True})
        self.assertEqual(typed_value(1), {"kind": "integer", "value": "1"})

    def test_nil_and_unresolved_are_distinct(self):
        self.assertEqual(typed_value(None, nil=True), {"kind": "nil", "value": None})
        with self.assertRaisesRegex(ValueError, "Non-nil null"):
            typed_value(None)
        with self.assertRaisesRegex(ValueError, "non-null"):
            typed_value(0, nil=True)
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            typed_value(Decimal("NaN"))

    def test_microseconds_and_timezone_presence_survive(self):
        naive = datetime(2025, 6, 30, 12, 34, 56, 123456)
        self.assertEqual(typed_value(naive)["microsecond"], 123456)
        self.assertIsNone(typed_value(naive)["timezone_offset_seconds"])
        self.assertEqual(
            typed_value(naive.replace(tzinfo=timezone.utc))["timezone_offset_seconds"], 0
        )
        self.assertEqual(
            typed_value(naive.replace(tzinfo=timezone(-timedelta(hours=5, minutes=30))))[
                "timezone_offset_seconds"
            ],
            -19800,
        )

    def test_context_date_only_boundary_is_distinct_from_datetime(self):
        self.assertEqual(checked_boundary("2025-06-30", True), "2025-07-01T00:00:00")
        self.assertEqual(checked_boundary("2025-06-30", False), "2025-06-30T00:00:00")
        self.assertEqual(
            checked_boundary("2025-06-30T00:00:00-05:30", True), "2025-06-30T00:00:00-05:30"
        )
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            checked_boundary("2025-06-30T00:00:00.1234567", True)

    def test_string_whitespace_is_not_rewritten(self):
        self.assertEqual(typed_value("  words\n  "), {"kind": "string", "value": "  words\n  "})


class SourceBinding(unittest.TestCase):
    def test_corrupted_geometry_is_rejected(self):
        from provenance.xbrl_occurrences import occurrence_sidecar

        raw = b'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:s="urn:s"><body><ix:nonNumeric id="a" name="s:A" contextRef="c">a</ix:nonNumeric><ix:nonNumeric id="b" name="s:A" contextRef="c">b</ix:nonNumeric></body></html>'
        tables = json.dumps(
            {
                "version": "native-html-tables-v2",
                "original_sha256": hashlib.sha256(raw).hexdigest(),
                "tables": [],
            }
        ).encode()
        original = occurrence_sidecar(raw, tables)
        self.assertEqual(verified_occurrences(raw, original, tables), original)
        for key, value in (
            ("byte_start", 0),
            ("source_bytes_sha256", "bad"),
            ("id", "b"),
            ("element_path", []),
            ("table_mapping", {"cell_id": "invented"}),
        ):
            corrupt = copy.deepcopy(original)
            corrupt["facts"][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "geometry differs"):
                verified_occurrences(raw, corrupt, tables)


if __name__ == "__main__":
    unittest.main()
