"""Where each room is hosted, as a contract - not as a dict. Maps a room id to
the server hosting it, so a gateway can route a join to the right server once
games run on more than one instance.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

_KEY_PREFIX = "room:"


@runtime_checkable
class RoomDirectory(Protocol):
    def put(self, room_id, server_id) -> None:
        ...

    def get(self, room_id) -> "str | None":
        ...

    def remove(self, room_id) -> None:
        ...


class InMemoryRoomDirectory:
    def __init__(self):
        self._hosts = {}

    def put(self, room_id, server_id):
        self._hosts[room_id] = server_id

    def get(self, room_id):
        return self._hosts.get(room_id)

    def remove(self, room_id):
        self._hosts.pop(room_id, None)


class RedisRoomDirectory:  # pragma: no cover - redis shell, exercised by running it
    def __init__(self, url):
        import redis

        self._redis = redis.Redis.from_url(url, decode_responses=True)

    def put(self, room_id, server_id):
        self._redis.set(_KEY_PREFIX + room_id, server_id)

    def get(self, room_id):
        return self._redis.get(_KEY_PREFIX + room_id)

    def remove(self, room_id):
        self._redis.delete(_KEY_PREFIX + room_id)
