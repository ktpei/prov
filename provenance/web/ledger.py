"""Append-only live-spend ledger with a hard cap on new live turns."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

MAX_TURN_USD = 0.10
MIN_TURN_USD = 0.01


class Ledger:
    def __init__(self, path, cap_usd):
        self.path, self.cap = Path(path), float(cap_usd)
        self.lock = threading.Lock()
        self._total = 0.0
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    if row.get("mode") == "live":
                        self._total += float(row["cost_usd"])

    def total(self):
        return self._total

    def remaining(self):
        return max(0.0, self.cap - self._total)

    def turn_budget(self, max_turn=MAX_TURN_USD):
        remaining = self.remaining()
        return None if remaining < MIN_TURN_USD else min(max_turn, remaining)

    def record(self, turn_id, cost_usd, *, uncertain, model, mode, status):
        row = {
            "time": datetime.now(timezone.utc).isoformat(),
            "turn_id": turn_id,
            "cost_usd": float(cost_usd),
            "uncertain": bool(uncertain),
            "model": model,
            "mode": mode,
            "status": status,
        }
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            if mode == "live":
                self._total += float(cost_usd)
