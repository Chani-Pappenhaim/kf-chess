"""The matchmaking queue as a contract, holding only an id and a rating per
seeker so it can move to a shared Redis. Wait time is aged per server, not here.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MatchmakingQueue(Protocol):
    def add(self, seeker_id, rating) -> None:
        ...

    def pop_match(self, rating) -> "str | None":
        ...

    def remove(self, seeker_id) -> None:
        ...


class _Entry:
    __slots__ = ("seeker_id", "rating")

    def __init__(self, seeker_id, rating):
        self.seeker_id = seeker_id
        self.rating = rating


class InMemoryMatchmakingQueue:
    def __init__(self, config):
        self._config = config
        self._waiting = []

    def add(self, seeker_id, rating):
        self._waiting.append(_Entry(seeker_id, rating))

    def pop_match(self, rating):
        within = self._config.MATCHMAKING_ELO_RANGE
        for entry in self._waiting:
            if abs(entry.rating - rating) <= within:
                self._waiting.remove(entry)
                return entry.seeker_id
        return None

    def remove(self, seeker_id):
        self._waiting = [e for e in self._waiting if e.seeker_id != seeker_id]
