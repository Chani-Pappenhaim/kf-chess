"""Every room the server is running, kept by id.

The one place that holds more than one game. It opens rooms on demand (each with
a fresh id and a fresh game, built by the injected factory), finds a room by the
id a client typed, and on every tick advances all of them and forgets any that
have emptied out.

The factory is injected so the lobby knows nothing of how a room is wired - a
test hands it a fake, the server hands it the real per-room graph.
"""
from __future__ import annotations


class Lobby:
    def __init__(self, room_factory):
        self._new_room = room_factory
        self._rooms = {}
        self._next_id = 1  # room ids count up, so they are stable and readable

    def create(self):
        """Open a fresh room with a new id and hand it back."""
        room_id = str(self._next_id)
        self._next_id += 1
        room = self._new_room(room_id)
        self._rooms[room_id] = room
        return room

    def room(self, room_id):
        """The room with this id, or None if there is none."""
        return self._rooms.get(room_id)

    def tick(self, dt):
        """Advance every room, then drop any that no one is left in."""
        for room in list(self._rooms.values()):
            room.tick(dt)
        self._rooms = {
            room_id: room for room_id, room in self._rooms.items() if not room.is_empty
        }
