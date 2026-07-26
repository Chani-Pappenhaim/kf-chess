"""The "Play" button's other half: pairing two players who want a game.

A seeker who presses Play is set against anyone already waiting whose rating is
within MATCHMAKING_ELO_RANGE; find one and a fresh room opens for the two of them
(the one who waited is White, the newcomer Black). Find none and the seeker
joins the queue, where each tick ages them - once MATCHMAKING_TIMEOUT_MS passes
with no match, they are told none was found and drop out.

The wait is measured from tick(dt), never wall-clock, so this counts on the same
one clock the rest of the server does.
"""
from __future__ import annotations

from protocol.messages import NoOpponent, encode


class _Seeker:
    __slots__ = ("session", "waited")

    def __init__(self, session):
        self.session = session
        self.waited = 0  # ms spent waiting, aged by tick


class Matchmaker:
    def __init__(self, lobby, config):
        self._lobby = lobby
        self._config = config
        self._waiting = []

    def seek(self, session):
        """Pair `session` with a waiting seeker in rating range, or queue it."""
        match = self._match_for(session.account.rating)
        if match is None:
            self._waiting.append(_Seeker(session))
            return
        self._waiting.remove(match)
        room = self._lobby.create()
        room.join(match.session)  # waited longer -> White
        room.join(session)        # newcomer -> Black

    def cancel(self, session):
        """Drop a seeker who disconnected before a match was found."""
        self._waiting = [s for s in self._waiting if s.session is not session]

    def tick(self, dt):
        """Age every waiting seeker; time out those who have waited too long."""
        for seeker in list(self._waiting):
            seeker.waited += dt
            if seeker.waited >= self._config.MATCHMAKING_TIMEOUT_MS:
                self._waiting.remove(seeker)
                seeker.session.send(encode(NoOpponent()))

    def _match_for(self, rating):
        within = self._config.MATCHMAKING_ELO_RANGE
        for seeker in self._waiting:
            if abs(seeker.session.account.rating - rating) <= within:
                return seeker
        return None
