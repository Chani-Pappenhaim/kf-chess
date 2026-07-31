"""Every room this server is running, kept by id.

Opens rooms on demand (each with a fresh id and a fresh game, built by the
injected factory), finds a room by the id a client typed, and on every tick
advances all of them and forgets any that have emptied out. Which server a
room's id hashes to (see allocator.GameAllocator) is a separate question this
class knows nothing about - it only runs whatever rooms it is asked to.

`snapshots` + `rehydrate`, when both given, let `room()` recover a room this
process has no memory of from a saved position (server/room_snapshots.py) -
the process that was running it died, but another (or the same, restarted)
picked the room back up rather than losing the game outright.
"""
from __future__ import annotations

from server.active_rooms import InMemoryActiveRooms


class Lobby:
    def __init__(self, room_factory, server_id, active_rooms=None, snapshots=None, rehydrate=None):
        self._new_room = room_factory
        self._server_id = server_id
        self._active_rooms = active_rooms or InMemoryActiveRooms()
        self._snapshots = snapshots
        self._rehydrate = rehydrate
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
        self._active_rooms.mark_started(room_id)
        return room

    def get_or_create(self, room_id):
        """The room with this id, creating it if this is the first to arrive."""
        return self._rooms.get(room_id) or self.create(room_id)

    def room(self, room_id):
        """The room with this id: live in memory, rehydrated from its last
        saved snapshot if this process lost it, or None if there truly is
        no such room."""
        room = self._rooms.get(room_id)
        if room is not None:
            return room
        return self._rehydrate_room(room_id)

    def _rehydrate_room(self, room_id):
        if self._snapshots is None or self._rehydrate is None:
            return None
        snapshot = self._snapshots.load(room_id)
        if snapshot is None:
            return None
        room = self._rehydrate(room_id, snapshot)
        self._rooms[room_id] = room
        self._active_rooms.mark_started(room_id)
        return room

    def room_count(self):
        """How many rooms are live here right now - the autoscaling signal."""
        return len(self._rooms)

    def fleet_room_count(self):
        """How many rooms are live anywhere in the fleet - a dashboard's view,
        not this one process's; identical to room_count() when not distributed."""
        return self._active_rooms.count()

    def tick(self, dt):
        """Advance every room, then drop any that no one is left in."""
        for room in list(self._rooms.values()):
            room.tick(dt)
        emptied = [room_id for room_id, room in self._rooms.items() if room.is_empty]
        for room_id in emptied:
            del self._rooms[room_id]
            self._active_rooms.mark_ended(room_id)
            if self._snapshots is not None:
                self._snapshots.delete(room_id)  # a genuinely finished room, not a crash
