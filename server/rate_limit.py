"""A plain token bucket, and a bucket per key - no new infrastructure, since
what needs limiting (one WS connection's message rate, one IP's login rate)
never needs to be shared across processes the way a room or a queue does.

`clock` is injected (defaults to `time.monotonic`) so a test can drive it
without a real `time.sleep`.
"""
from __future__ import annotations

import time


class TokenBucket:
    def __init__(self, capacity, refill_per_second, clock=time.monotonic):
        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._clock = clock
        self._tokens = float(capacity)
        self._last = clock()

    def allow(self):
        """Whether one more action is allowed right now - consumes a token if
        so, refilling first for however long has passed since the last check."""
        now = self._clock()
        self._tokens = min(
            self._capacity, self._tokens + (now - self._last) * self._refill_per_second
        )
        self._last = now
        if self._tokens < 1:
            return False
        self._tokens -= 1
        return True


class RateLimiter:
    """One bucket per key, created the first time that key is seen. A key
    that never sends anything costs nothing - buckets are lazy, not
    pre-allocated for every possible connection or IP."""

    def __init__(self, capacity, refill_per_second, clock=time.monotonic):
        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._clock = clock
        self._buckets = {}

    def allow(self, key):
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(self._capacity, self._refill_per_second, self._clock)
            self._buckets[key] = bucket
        return bucket.allow()
