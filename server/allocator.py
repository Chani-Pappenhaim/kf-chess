"""Which Game Server a room lives on - a hash ring over the live pool, so
adding or removing a server remaps only the slice of keys near it, not the
whole pool. Placement is a pure function of the room id: no directory is
stored anywhere, because any server can compute it the same way.
"""
from __future__ import annotations

import hashlib
import secrets

_VIRTUAL_NODES = 100  # per server, so the ring is evenly covered
_ROOM_ID_BYTES = 4    # short enough to read aloud or type


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


def parse_pool(spec):
    """"id=address,id=address" -> {id: address}."""
    pairs = (entry.split("=", 1) for entry in spec.split(","))
    return {server_id.strip(): address.strip() for server_id, address in pairs}


def mint_room_id():
    return secrets.token_urlsafe(_ROOM_ID_BYTES)


def _hash(key):
    return int(hashlib.sha256(key.encode()).hexdigest(), 16)
