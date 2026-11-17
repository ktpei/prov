"""Actual synthetic FactReader authorization and independently anchored replay."""

import copy
import unittest
from unittest.mock import patch

import test_xbrl_reader

from provenance.fact_read_session import FactReadSession, digest, replay_fact_reads
from provenance.xbrl_reader import canonical, sha


class FactReadSessionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_xbrl_reader.FactReaderTests()
        self.fixture.setUp()

    def args(self, cutoff=None):
        f = self.fixture
        artifacts = (canonical(f.export).encode(), canonical(f.source).encode(), f.original)
        auth = {
            "source_id": "issuer",
            "original_sha256": sha(artifacts[2]),
            "export_sha256": sha(artifacts[0]),
            "source_sha256": sha(artifacts[1]),
            "reader": "exact-xbrl-fact-reader-v1",
            "as_of": cutoff,
        }
        return artifacts, {"authorization": auth, "run_id": "run-a"}

    def session(self, cutoff=None):
        args, kw = self.args(cutoff)
        return FactReadSession(*args, **kw)

    def replay(self, snapshot, **overrides):
        args, kw = self.args()
        return replay_fact_reads(
            *args,
            **{
                **kw,
                "snapshot": snapshot,
                "expected_snapshot_sha256": digest(snapshot),
                **overrides,
            },
        )

    def test_actual_full_read_immutable_and_replayed(self):
        session = self.session()
        record = session.read("f")
        original = session.snapshot()
        self.assertEqual(self.replay(original), original)
        delivery = original["deliveries"][0]
        self.assertEqual(delivery["payload"], self.fixture.reader().read("f")["payload"])
        self.assertEqual(delivery["disposition"], "delivered_not_semantically_admitted")
        self.assertNotIn("attributes", delivery)
        self.assertNotIn("model_visible", delivery)
        record["response"]["payload"]["fact"]["value"] = "forged"
        original["deliveries"].clear()
        self.assertEqual(len(session.snapshot()["deliveries"]), 1)
        self.assertNotEqual(record, session.snapshot()["reads"][0])
        second = session.read("f")
        self.assertNotEqual(second["id"], session.snapshot()["reads"][0]["id"])

    def test_unicode_chunks_full_equivalence_and_partial_not_delivered(self):
        self.fixture.export["facts"][0]["value"] = {"kind": "string", "value": 'é😀\\\n"' * 2500}
        session = self.session()
        record = session.read("f")
        self.assertEqual(record["response"]["status"], "deferred")
        self.assertFalse(session.snapshot()["deliveries"])
        start = 0
        while start is not None:
            record = session.read("f", start=start, length=997)
            start = record["response"]["next_start"]
        snapshot = session.snapshot()
        self.assertFalse(snapshot["pending"])
        self.assertEqual(
            snapshot["deliveries"][0]["payload"]["fact"], self.fixture.export["facts"][0]
        )
        self.assertEqual(self.replay(snapshot), snapshot)
        # Small values can be delivered either as one response or a complete chunk sequence.
        self.fixture.setUp()
        full, chunked = self.session(), self.session()
        full.read("f")
        start = 0
        while start is not None:
            start = chunked.read("f", start=start, length=300)["response"]["next_start"]
        self.assertEqual(
            full.snapshot()["deliveries"][0]["payload"],
            chunked.snapshot()["deliveries"][0]["payload"],
        )

    def test_gap_overlap_and_hash_drift_reject_atomically(self):
        session = self.session()
        session.read("f", start=0, length=100)
        before = session.snapshot()
        for start in (0, 99, 101, 200):
            with self.assertRaisesRegex(ValueError, "noncontiguous"):
                session.read("f", start=start, length=100)
            self.assertEqual(session.snapshot(), before)
        real = session._reader.read
        for field, value in (
            ("chunk_sha256", "0" * 64),
            ("payload_sha256", "0" * 64),
            ("source_metadata_sha256", "0" * 64),
            ("next_start", 999),
        ):
            response = real("f", start=100, length=100)
            response[field] = value
            with patch.object(session._reader, "read", return_value=response):
                with self.assertRaises(ValueError):
                    session.read("f", start=100, length=100)
            self.assertEqual(session.snapshot(), before)

    def test_cutoff_and_artifact_authorization(self):
        blocked = self.session("2025-07-01T00:00:00Z")
        record = blocked.read("unknown")
        self.assertEqual(record["response"]["status"], "availability_blocked")
        self.assertFalse(blocked.snapshot()["deliveries"])
        with self.assertRaises(TypeError):
            blocked.read("f", as_of=None)
        args, kw = self.args()
        for field in ("source_id", "original_sha256", "export_sha256", "source_sha256", "reader"):
            altered = copy.deepcopy(kw)
            altered["authorization"][field] = "forged"
            with self.assertRaises(ValueError):
                FactReadSession(*args, **altered)

    def test_quarantine_nil_and_zero_are_diagnostics(self):
        for value in ({"kind": "nil", "value": None}, {"kind": "decimal", "value": "0"}):
            self.fixture.export["facts"][0]["value"] = value
            self.fixture.export["facts"][0]["disposition"] = "quarantined_inconsistent_duplicate"
            self.fixture.export["duplicate_groups"][0]["inconsistent"] = True
            session = self.session()
            session.read("f")
            payload = session.snapshot()["deliveries"][0]["payload"]
            self.assertEqual(payload["fact"]["value"], value)
            self.assertEqual(payload["fact"]["disposition"], "quarantined_inconsistent_duplicate")

    def test_payload_limit_and_tampered_full_read_are_atomic(self):
        session = self.session()
        response = session._reader.read("f")
        for field, value in (("payload_characters", 256001), ("payload_sha256", "0" * 64)):
            changed = copy.deepcopy(response)
            changed[field] = value
            with patch.object(session._reader, "read", return_value=changed):
                with self.assertRaises(ValueError):
                    session.read("f")
            self.assertFalse(session.snapshot()["reads"])
        self.fixture.export["facts"][0]["value"] = {"kind": "string", "value": "x" * 256001}
        with self.assertRaisesRegex(ValueError, "size limit"):
            self.session().read("f")

    def test_replay_rejects_tampering_and_missing_trailing_inventory(self):
        session = self.session()
        session.read("f")
        session.read("f")
        snapshot = session.snapshot()
        anchored = digest(snapshot)
        removed = copy.deepcopy(snapshot)
        removed["reads"].pop()
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.replay(removed, expected_snapshot_sha256=anchored)
        for section in ("reads", "deliveries"):
            changed = copy.deepcopy(snapshot)
            changed[section][0]["id"] = "forged"
            with self.assertRaises(ValueError):
                self.replay(changed)
        changed = copy.deepcopy(snapshot)
        changed["reads"][0]["response"]["payload"]["unit"] = {"fake": "EUR"}
        with self.assertRaisesRegex(ValueError, "replay"):
            self.replay(changed)
        with self.assertRaisesRegex(ValueError, "identity"):
            self.replay(snapshot, run_id="run-b")
        args, kw = self.args()
        kw["authorization"]["as_of"] = "2026-11-16T12:00:00Z"
        with self.assertRaisesRegex(ValueError, "identity"):
            self.replay(snapshot, **kw)

    def test_multiple_pending_payloads_share_reconstruction_limit(self):
        f = self.fixture
        f.original = f.original.replace(b"</body>", b'<span id="g">1</span></body>')
        for record in (f.source, f.source["availability"], f.export):
            record["original_sha256"] = sha(f.original)
        f.export["facts"][0]["value"] = {"kind": "string", "value": "x" * 150000}
        second = copy.deepcopy(f.export["facts"][0])
        second["id"] = "g"
        f.export["facts"].append(second)
        session = self.session()
        session.read("f")
        before = session.snapshot()
        with self.assertRaisesRegex(ValueError, "Aggregate"):
            session.read("g")
        self.assertEqual(session.snapshot(), before)
        start = 0
        while start is not None:
            start = session.read("f", start=start)["response"]["next_start"]
        self.assertFalse(session.snapshot()["pending"])
        self.assertEqual(session.read("g")["response"]["status"], "deferred")
