"""Deterministic spending and wall-clock controls."""

import math
import signal
import time
from contextlib import contextmanager
from dataclasses import dataclass


class LimitReached(Exception):
    """Stop the run, rather than inviting the model to retry a hard limit."""


class DeadlineReached(LimitReached):
    pass


def positive(value, name):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return number


@dataclass
class Budget:
    limit: float
    charged: float = 0.0
    uncertain: bool = False

    def __post_init__(self):
        positive(self.limit, "budget")

    def reserve(self, amount):
        amount = positive(amount, "reservation")
        if self.charged + amount > self.limit + 1e-12:
            raise LimitReached("spend_limit")
        self.charged += amount
        return amount

    def settle(self, reserved, actual):
        if not isinstance(actual, (int, float)) or not math.isfinite(actual) or actual < 0:
            self.uncertain = True
            raise LimitReached("invalid_billing_usage")
        self.charged += actual - reserved
        if actual > reserved + 1e-12:
            self.uncertain = True
            raise LimitReached("reservation_exceeded")


@contextmanager
def deadline(seconds):
    """Hard wall-clock deadline for this single-threaded macOS/Linux CLI."""
    positive(seconds, "timeout")
    if not hasattr(signal, "setitimer"):
        raise ValueError("Hard deadlines currently require macOS or Linux")

    def expired(signum, frame):
        raise DeadlineReached("wall_clock_limit")

    old_handler = signal.signal(signal.SIGALRM, expired)
    old_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    started = time.monotonic()
    try:
        yield lambda: max(0.001, seconds - (time.monotonic() - started))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        if old_timer[0]:
            signal.setitimer(
                signal.ITIMER_REAL,
                max(0.001, old_timer[0] - (time.monotonic() - started)),
                old_timer[1],
            )
