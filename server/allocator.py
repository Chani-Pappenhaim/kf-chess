"""Which Game Server should host a fresh session - a hash ring over the live
pool, so adding or removing a server remaps only the slice of keys near it,
not the whole pool.
"""
from __future__ import annotations

import hashlib

_VIRTUAL_NODES = 100  # per server, so the ring is evenly covered


class GameAllocator:
    def __init__(self, servers):
        self._ring = {
            _hash(f"{server}-{i}"): server
            for server in servers
            for i in range(_VIRTUAL_NODES)
        }
        self._points = sorted(self._ring)

    def for_key(self, key):
        """The server id `key` lands on: the next point clockwise on the ring,
        wrapping back to the first past the highest point."""
        point = _hash(key)
        for ring_point in self._points:
            if point <= ring_point:
                return self._ring[ring_point]
        return self._ring[self._points[0]]


def _hash(key):
    return int(hashlib.sha256(key.encode()).hexdigest(), 16)
