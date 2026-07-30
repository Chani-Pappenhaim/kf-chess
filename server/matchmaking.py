"""Pairing two players by rating, then placing the room the same way any room
is placed: hashing its id (GameAllocator) decides which Game Server it lives
on. Both matched players are settled the same way regardless of whether they
started out on that server, on each other's, or on neither: seated directly
if they are already there, or told where to reconnect if not - and whichever
server the room actually belongs to is told to open it, even before either
player arrives. Each server ages only its own seekers, so a shared queue is
not aged many times over.
"""
from __future__ import annotations

from protocol.messages import NoOpponent, Redirected, encode
from server.allocator import mint_room_id

ROOM_ASSIGNED_CHANNEL = "matchmaking:room-assigned"


class _Waiting:
    __slots__ = ("session", "waited")

    def __init__(self, session):
        self.session = session
        self.waited = 0


class Matchmaker:
    def __init__(self, lobby, queue, config, allocator, server_id, bus=None):
        self._lobby = lobby
        self._queue = queue
        self._config = config
        self._allocator = allocator
        self._server_id = server_id
        self._bus = bus  # None: every server in the pool is this one server
        self._waiting = {}  # id -> _Waiting

    def seek(self, session):
        seeker_id, rating = session.account.username, session.account.rating
        match = self._queue.pop_match(rating)
        if match is None:
            self._queue.add(seeker_id, rating)
            self._waiting[seeker_id] = _Waiting(session)
            return
        match_id, match_rating = match
        opponent = self._waiting.pop(match_id, None)
        if opponent is None and self._bus is None:
            # theirs, and no bus to reach their server - both wait normally
            self._queue.add(match_id, match_rating)
            self._queue.add(seeker_id, rating)
            self._waiting[seeker_id] = _Waiting(session)
            return
        room_id = mint_room_id()
        target = self._allocator.for_key(room_id)
        if opponent is not None:
            self._settle(opponent.session, room_id, target)  # waited longer -> White
            self._settle(session, room_id, target)            # newcomer -> Black
        else:
            self._settle(session, room_id, target)
        # Tell the target server to open the room even if neither of us is it,
        # and tell a foreign opponent's own server about them either way.
        if (opponent is None or target != self._server_id) and self._bus is not None:
            self._bus.publish(ROOM_ASSIGNED_CHANNEL, {
                "room_id": room_id,
                "target": target,
                "seeker_id": match_id if opponent is None else None,
            })

    def cancel(self, session):
        seeker_id = session.account.username
        self._queue.remove(seeker_id)
        self._waiting.pop(seeker_id, None)

    def tick(self, dt):
        if self._bus is not None:
            for message in self._bus.poll(ROOM_ASSIGNED_CHANNEL):
                self._accept(message)
        for seeker_id, waiting in list(self._waiting.items()):
            waiting.waited += dt
            if waiting.waited >= self._config.MATCHMAKING_TIMEOUT_MS:
                self._queue.remove(seeker_id)
                del self._waiting[seeker_id]
                waiting.session.send(encode(NoOpponent()))

    def _settle(self, session, room_id, target):
        """Seat `session` in `room_id` if it is already hosted here, else tell
        them where to reconnect - the same rule for every matched player."""
        if target == self._server_id:
            self._lobby.get_or_create(room_id).join(session)
        else:
            session.send(encode(Redirected(room_id)))

    def _accept(self, message):
        """A room was assigned somewhere: open it here if we are the target
        (even before anyone has arrived), and settle a named foreign seeker
        of our own, if this match involves one."""
        if message["target"] == self._server_id:
            self._lobby.get_or_create(message["room_id"])
        seeker_id = message["seeker_id"]
        if seeker_id is not None:
            waiting = self._waiting.pop(seeker_id, None)
            if waiting is not None:
                self._settle(waiting.session, message["room_id"], message["target"])
