import tempfile
import unittest
from pathlib import Path

from provenance.web.ledger import Ledger


class LedgerTests(unittest.TestCase):
    def test_ledger_caps_and_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "cost-log.jsonl"
            ledger = Ledger(path, 0.20)
            self.assertEqual(ledger.turn_budget(), 0.10)
            ledger.record("t1", 0.15, uncertain=False, model="m", mode="live", status="completed")
            self.assertAlmostEqual(ledger.remaining(), 0.05)
            self.assertAlmostEqual(ledger.turn_budget(), 0.05)
            ledger.record("t2", 0.045, uncertain=True, model="m", mode="live", status="failed")
            self.assertIsNone(ledger.turn_budget())
            ledger.record("t3", 0.0, uncertain=False, model="r", mode="replay", status="completed")
            reloaded = Ledger(path, 0.20)
            self.assertAlmostEqual(reloaded.total(), 0.195)
            self.assertEqual(len(path.read_text().splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
