"""Small in-process rate limiter for sensitive endpoints.

This protects the current single-worker deployment. Multi-worker deployments
must replace the in-memory store with a shared Redis-backed implementation.
"""
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> RateLimitDecision:
        now = monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - events[0])))
                return RateLimitDecision(False, retry_after)

            return RateLimitDecision(True)

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._events[key].append(monotonic())

    def clear(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)
