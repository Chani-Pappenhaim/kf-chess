"""Every room this server is running, kept by id.

Opens rooms on demand (each with a fresh id and a fresh game, built by the
injected factory), finds a room by the id a client typed, and on every tick
advances all of them and forgets any that have emptied out. Each room is also
registered in the RoomDirectory under this server's id, so a gateway can find
which server hosts it once games run on more than one instance.
"""
from __future__ import annotations


class Lobby:
    def __init__(self, room_factory, directory, server_id):
        self._new_room = room_factory
        self._directory = directory
        self._server_id = server_id
        self._rooms = {}
        self._next_id = 1  # room ids count up per server, so they stay readable

    def create(self):
        """Open a fresh room with a new id and hand it back."""
        room_id = f"{self._server_id}-{self._next_id}"
        self._next_id += 1
        room = self._new_room(room_id)
        self._rooms[room_id] = room
        self._directory.put(room_id, self._server_id)
        return room

    def room(self, room_id):
        """The room with this id, or None if there is none."""
        return self._rooms.get(room_id)

    def tick(self, dt):
        """Advance every room, then drop any that no one is left in."""
        for room in list(self._rooms.values()):
            room.tick(dt)
        emptied = [room_id for room_id, room in self._rooms.items() if room.is_empty]
        for room_id in emptied:
            del self._rooms[room_id]
            self._directory.remove(room_id)
