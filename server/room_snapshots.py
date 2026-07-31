"""A room's live position, mirrored so it survives the process that was
running it. Deliberately not a full save-state: board occupancy and who is
seated where, not per-piece cooldowns or an in-flight move's exact progress -
see server/__main__.py::build_room for what a rehydrated room actually
restores, and why that scope was chosen over full fidelity.
"""
from __future__ import annotations

import json
from typing import Protocol, runtime_checkable

_KEY_PREFIX = "room-snapshot:"


@runtime_checkable
class RoomSnapshots(Protocol):
    def save(self, room_id, snapshot) -> None:
        ...

    def load(self, room_id):
        ...

    def delete(self, room_id) -> None:
        ...


class InMemoryRoomSnapshots:
    def __init__(self):
        self._snapshots = {}

    def save(self, room_id, snapshot):
        self._snapshots[room_id] = snapshot

    def load(self, room_id):
        return self._snapshots.get(room_id)

    def delete(self, room_id):
        self._snapshots.pop(room_id, None)


class RedisRoomSnapshots:  # pragma: no cover - redis shell, exercised by running it
    def __init__(self, url):
        import redis

        self._redis = redis.Redis.from_url(url, decode_responses=True)

    def save(self, room_id, snapshot):
        self._redis.set(_KEY_PREFIX + room_id, json.dumps(snapshot))

    def load(self, room_id):
        raw = self._redis.get(_KEY_PREFIX + room_id)
        return None if raw is None else json.loads(raw)

    def delete(self, room_id):
        self._redis.delete(_KEY_PREFIX + room_id)
