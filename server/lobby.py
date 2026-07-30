"""Every room this server is running, kept by id.

Opens rooms on demand (each with a fresh id and a fresh game, built by the
injected factory), finds a room by the id a client typed, and on every tick
advances all of them and forgets any that have emptied out. Which server a
room's id hashes to (see allocator.GameAllocator) is a separate question this
class knows nothing about - it only runs whatever rooms it is asked to.
"""
from __future__ import annotations


class Lobby:
    def __init__(self, room_factory, server_id):
        self._new_room = room_factory
        self._server_id = server_id
        self._rooms = {}
        self._next_id = 1  # room ids count up per server, so they stay readable

    def create(self, room_id=None):
        """Open a fresh room and hand it back. `room_id` is given when it was
        already decided elsewhere (a routed CreateRoom, a matched pair);
        otherwise a local id is minted."""
        if room_id is None:
            room_id = f"{self._server_id}-{self._next_id}"
            self._next_id += 1
        room = self._new_room(room_id)
        self._rooms[room_id] = room
        return room

    def get_or_create(self, room_id):
        """The room with this id, creating it if this is the first to arrive."""
        return self._rooms.get(room_id) or self.create(room_id)

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
