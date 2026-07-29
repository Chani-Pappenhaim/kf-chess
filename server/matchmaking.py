"""The "Play" button's other half: pairing two players who want a game.

A seeker who presses Play is set against anyone already waiting whose rating is
within MATCHMAKING_ELO_RANGE; find one and a fresh room opens for the two of them
(the one who waited is White, the newcomer Black). Find none and the seeker
joins the queue, where each tick ages them - once MATCHMAKING_TIMEOUT_MS passes
with no match, they are told none was found and drop out.

The queue itself is a MatchmakingQueue holding only an id and a rating; the live
sessions stay here, keyed by id, so a queue of plain data can move to Redis while
reaching a seeker stays local. The wait is measured from tick(dt), never
wall-clock, so this counts on the same one clock the rest of the server does.
"""
from __future__ import annotations

from protocol.messages import NoOpponent, encode


class Matchmaker:
    def __init__(self, lobby, queue):
        self._lobby = lobby
        self._queue = queue
        self._sessions = {}  # seeker id -> session, to reach a waiting player

    def seek(self, session):
        """Pair `session` with a waiting seeker in rating range, or queue it."""
        seeker_id = session.account.username
        match_id = self._queue.pop_match(session.account.rating)
        if match_id is None:
            self._queue.add(seeker_id, session.account.rating)
            self._sessions[seeker_id] = session
            return
        opponent = self._sessions.pop(match_id)
        room = self._lobby.create()
        room.join(opponent)  # waited longer -> White
        room.join(session)   # newcomer -> Black

    def cancel(self, session):
        """Drop a seeker who disconnected before a match was found."""
        seeker_id = session.account.username
        self._queue.remove(seeker_id)
        self._sessions.pop(seeker_id, None)

    def tick(self, dt):
        """Age every waiting seeker; tell those who waited too long none came."""
        for seeker_id in self._queue.age(dt):
            self._sessions.pop(seeker_id).send(encode(NoOpponent()))
