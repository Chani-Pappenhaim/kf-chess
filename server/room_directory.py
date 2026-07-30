"""Where each room is hosted, as a contract - not as a dict. Maps a room id to
the server hosting it, so a gateway can route a join to the right server once
games run on more than one instance.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


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
