"""Pairing two players: a seeker meets anyone waiting within MATCHMAKING_ELO_RANGE,
else joins the queue and times out after MATCHMAKING_TIMEOUT_MS. Each server ages
only its own seekers, so a shared queue is not aged many times over.
"""
from __future__ import annotations

from protocol.messages import NoOpponent, encode


class _Waiting:
    __slots__ = ("session", "waited")

    def __init__(self, session):
        self.session = session
        self.waited = 0


class Matchmaker:
    def __init__(self, lobby, queue, config):
        self._lobby = lobby
        self._queue = queue
        self._config = config
        self._waiting = {}  # id -> _Waiting

    def seek(self, session):
        seeker_id = session.account.username
        match_id = self._queue.pop_match(session.account.rating)
        if match_id is None:
            self._queue.add(seeker_id, session.account.rating)
            self._waiting[seeker_id] = _Waiting(session)
            return
        opponent = self._waiting.pop(match_id).session
        room = self._lobby.create()
        room.join(opponent)  # waited longer -> White
        room.join(session)   # newcomer -> Black

    def cancel(self, session):
        seeker_id = session.account.username
        self._queue.remove(seeker_id)
        self._waiting.pop(seeker_id, None)

    def tick(self, dt):
        for seeker_id, waiting in list(self._waiting.items()):
            waiting.waited += dt
            if waiting.waited >= self._config.MATCHMAKING_TIMEOUT_MS:
                self._queue.remove(seeker_id)
                del self._waiting[seeker_id]
                waiting.session.send(encode(NoOpponent()))
