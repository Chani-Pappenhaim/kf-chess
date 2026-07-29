"""The matchmaking queue as a contract - not as a list.

The Matchmaker depends on this, never on where the queue lives, so the waiting
seekers can sit in this process's memory today and in a shared Redis once the
server runs as more than one instance. It holds only what pairing needs - an id
and a rating per seeker - never a live session, which is what lets a networked
implementation keep the queue as plain data.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MatchmakingQueue(Protocol):
    def add(self, seeker_id, rating) -> None:
        """Enqueue a seeker waiting for a game."""
        ...

    def pop_match(self, rating) -> "str | None":
        """Remove and return a waiting seeker within rating range, or None."""
        ...

    def remove(self, seeker_id) -> None:
        """Drop a seeker who left before a match was found."""
        ...

    def age(self, dt) -> tuple:
        """Advance every wait by `dt`; return and drop those now timed out."""
        ...


class _Waiter:
    __slots__ = ("seeker_id", "rating", "waited")

    def __init__(self, seeker_id, rating):
        self.seeker_id = seeker_id
        self.rating = rating
        self.waited = 0  # ms spent waiting, aged by `age`


class InMemoryMatchmakingQueue:
    """The queue held in this process - a single server's whole world today."""

    def __init__(self, config):
        self._config = config
        self._waiting = []

    def add(self, seeker_id, rating):
        self._waiting.append(_Waiter(seeker_id, rating))

    def pop_match(self, rating):
        within = self._config.MATCHMAKING_ELO_RANGE
        for waiter in self._waiting:
            if abs(waiter.rating - rating) <= within:
                self._waiting.remove(waiter)
                return waiter.seeker_id
        return None

    def remove(self, seeker_id):
        self._waiting = [w for w in self._waiting if w.seeker_id != seeker_id]

    def age(self, dt):
        timed_out = []
        for waiter in list(self._waiting):
            waiter.waited += dt
            if waiter.waited >= self._config.MATCHMAKING_TIMEOUT_MS:
                self._waiting.remove(waiter)
                timed_out.append(waiter.seeker_id)
        return tuple(timed_out)
