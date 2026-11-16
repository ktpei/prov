import copy
import json
import unittest

from provenance.xbrl_reader import MAX_RESPONSE_CHARACTERS, FactReader, canonical, sha


class FactReaderTests(unittest.TestCase):
    def setUp(self):
        self.original = b'<html xmlns="http://www.w3.org/1999/xhtml"><body><span id="f">0</span><span id="c">2025</span><span id="u">USD</span><span id="k">continued</span></body></html>'
        digest = sha(self.original)
        self.source = {
            "id": "issuer",
            "url": "https://issuer.test/copy",
            "reference_sec_url": "https://sec.test/filing",
            "artifact_class": "issuer_copy_not_sec_byte_equivalent",
            "original_sha256": digest,
            "availability": {
                "original_sha256": digest,
                "not_before": None,
                "observed_by": "2026-11-16T12:00:00Z",
                "basis": "Observed exact issuer bytes",
            },
        }
        self.export = {
            "version": "experimental-typed-xbrl-facts-v1",
            "original_sha256": digest,
            "canonical_url": "https://sec.test/filing",
            "facts": [
                {
                    "id": "f",
                    "context_id": "c",
                    "unit_id": "u",
                    "value": {"kind": "decimal", "value": "-0.00"},
                    "disposition": "schema_valid_source_bound",
                    "source_occurrence": {"continuation_fragments": [{"id": "k"}]},
                }
            ],
            "contexts": {
                "c": {
                    "reported_period": {"instant": "2025-06-30"},
                    "reported_dimensions": [{"axis": "{axis}A", "member": "{member}B"}],
                }
            },
            "units": {"u": {"numerator": ["{iso}USD"], "denominator": []}},
            "continuations": [{"id": "k", "referenced_by": "f"}],
            "duplicate_groups": [{"occurrences": ["f", "other"], "inconsistent": False}],
            "default_scope_note": "no inferred defaults",
            "normalization_note": "no rescale",
            "lexical_note": "assembled is not original",
        }

    def reader(self):
        exported, source = canonical(self.export).encode(), canonical(self.source).encode()
        return FactReader(
            exported, source, self.original, export_sha256=sha(exported), source_sha256=sha(source)
        )

    def test_complete_preserves_value_context_unit_groups_and_original_fragments(self):
        reader = self.reader()
        response = reader.read("f")
        self.assertEqual(response["status"], "complete")
        payload = response["payload"]
        for key, value in (
            ("fact", self.export["facts"][0]),
            ("context", self.export["contexts"]["c"]),
            ("unit", self.export["units"]["u"]),
            ("duplicate_groups", self.export["duplicate_groups"]),
        ):
            self.assertEqual(payload[key], value)
        for fragment in payload["original_fragments"]:
            raw = self.original[fragment["byte_start"] : fragment["byte_end"]]
            self.assertEqual(fragment["text"].encode(), raw)
            self.assertEqual(fragment["sha256"], sha(raw))
        self.assertEqual(
            {f["role"] for f in payload["original_fragments"]},
            {"fact", "context", "unit", "continuation"},
        )
        response["payload"]["fact"]["value"]["value"] = "99"
        self.assertEqual(reader.read("f")["payload"]["fact"]["value"]["value"], "-0.00")

    def test_large_unicode_payload_reconstructs_exactly(self):
        self.export["facts"][0]["value"] = {"kind": "string", "value": 'é😀\\\n"' * 5000}
        reader = self.reader()
        deferred = reader.read("f")
        self.assertEqual(deferred["status"], "deferred")
        self.assertFalse(deferred["complete_value_delivered"])
        chunks, start = [], 0
        while start is not None:
            response = reader.read("f", start=start, length=1000)
            self.assertLessEqual(len(canonical(response)), MAX_RESPONSE_CHARACTERS)
            self.assertEqual(sha(response["chunk"].encode()), response["chunk_sha256"])
            self.assertFalse(response["complete_value_delivered"])
            chunks.append(response["chunk"])
            start = response["next_start"]
        full = "".join(chunks)
        self.assertEqual(len(full), deferred["payload_characters"])
        self.assertEqual(sha(full.encode()), deferred["payload_sha256"])
        self.assertEqual(json.loads(full)["fact"]["value"], self.export["facts"][0]["value"])

    def test_availability_blocks_before_identity_lookup(self):
        reader = self.reader()
        blocked = reader.read("unknown", as_of="2025-07-01T00:00:00Z")
        self.assertEqual(blocked["status"], "availability_blocked")
        self.assertNotIn("payload", blocked)
        self.assertNotIn("occurrence_id", blocked)
        self.assertEqual(reader.read("f", as_of="2026-11-16T12:00:00Z")["status"], "complete")
        self.assertEqual(blocked["source"]["artifact_class"], "issuer_copy_not_sec_byte_equivalent")

    def test_tampered_inputs_reject_against_trusted_receipts(self):
        exported, source = canonical(self.export).encode(), canonical(self.source).encode()
        for ex, so, raw in (
            (exported + b" ", source, self.original),
            (exported, source + b" ", self.original),
            (exported, source, self.original + b" "),
        ):
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                FactReader(ex, so, raw, export_sha256=sha(exported), source_sha256=sha(source))

    def test_quarantine_is_retained_and_missing_quarantine_rejects(self):
        self.export["duplicate_groups"][0]["inconsistent"] = True
        with self.assertRaisesRegex(ValueError, "not quarantined"):
            self.reader()
        self.export["facts"][0]["disposition"] = "quarantined_inconsistent_duplicate"
        self.assertEqual(
            self.reader().read("f")["payload"]["fact"]["disposition"],
            "quarantined_inconsistent_duplicate",
        )

    def test_invalid_ranges_unknown_ids_and_duplicate_ids_reject(self):
        reader = self.reader()
        for start, length in ((True, 1), (-1, 1), (10**9, 1), (0, True), (0, 0), (0, 4001)):
            with self.subTest(start=start, length=length), self.assertRaises(ValueError):
                reader.read("f", start=start, length=length)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            reader.read("unknown")
        self.export["facts"].append(copy.deepcopy(self.export["facts"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate occurrence"):
            self.reader()

    def test_oversized_metadata_rejects_atomically(self):
        self.source["title"] = "large" * 5000
        reader = self.reader()
        with self.assertRaisesRegex(ValueError, "response exceeds"):
            reader.read("f")
        with self.assertRaisesRegex(ValueError, "response exceeds"):
            reader.read("f", start=0, length=1)

    def test_reconstruction_gate_rejects_missing_or_substituted_references(self):
        from eval.scripts.check_xbrl_reader import verify_references

        payload = self.reader().read("f")["payload"]
        verify_references(payload, self.export["facts"][0], self.export, self.original)
        for field in ("continuations", "original_fragments"):
            changed = copy.deepcopy(payload)
            changed[field] = []
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_references(changed, self.export["facts"][0], self.export, self.original)
        changed = copy.deepcopy(payload)
        changed["original_fragments"][1]["role"] = "fact"
        with self.assertRaisesRegex(ValueError, "inventory differs"):
            verify_references(changed, self.export["facts"][0], self.export, self.original)

        for replacement in (
            {"byte_start": 0, "byte_end": 0, "text": "", "sha256": sha(b"")},
            {
                key: value
                for key, value in payload["original_fragments"][1].items()
                if key not in {"id", "role"}
            },
        ):
            changed = copy.deepcopy(payload)
            changed["original_fragments"][0].update(replacement)
            with self.assertRaisesRegex(ValueError, "node interval differs"):
                verify_references(changed, self.export["facts"][0], self.export, self.original)

    def test_nil_and_zero_remain_distinct(self):
        self.assertEqual(self.reader().read("f")["payload"]["fact"]["value"]["kind"], "decimal")
        self.export["facts"][0]["value"] = {"kind": "nil", "value": None}
        self.assertEqual(
            self.reader().read("f")["payload"]["fact"]["value"], {"kind": "nil", "value": None}
        )


if __name__ == "__main__":
    unittest.main()
