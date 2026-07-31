"""Which rooms are live right now, across the whole fleet - not who owns which
one (that's a pure hash, see allocator.GameAllocator computing it with no
state of its own), just presence: one place a dashboard can ask "how many
games are running anywhere" instead of scraping every server's /metrics.

Not a routing mechanism and not a substitute for it - a server that crashes
mid-game takes its live boards down with it regardless of what is registered
here (see docs/scale-architecture.md's reconnect note); this only lets the
fleet see that happen.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

_KEY = "active-rooms"


@runtime_checkable
class ActiveRooms(Protocol):
    def mark_started(self, room_id) -> None:
        ...

    def mark_ended(self, room_id) -> None:
        ...

    def count(self) -> int:
        ...


class InMemoryActiveRooms:
    def __init__(self):
        self._rooms = set()

    def mark_started(self, room_id):
        self._rooms.add(room_id)

    def mark_ended(self, room_id):
        self._rooms.discard(room_id)

    def count(self):
        return len(self._rooms)


class RedisActiveRooms:  # pragma: no cover - redis shell, exercised by running it
    def __init__(self, url):
        import redis

        self._redis = redis.Redis.from_url(url, decode_responses=True)

    def mark_started(self, room_id):
        self._redis.sadd(_KEY, room_id)

    def mark_ended(self, room_id):
        self._redis.srem(_KEY, room_id)

    def count(self):
        return self._redis.scard(_KEY)
