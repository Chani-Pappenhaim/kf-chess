"""The matchmaking queue as a contract, holding only an id and a rating per
seeker so it can move to a shared Redis. Wait time is aged per server, not here.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

_KEY = "matchmaking:queue"


@runtime_checkable
class MatchmakingQueue(Protocol):
    def add(self, seeker_id, rating) -> None:
        ...

    def pop_match(self, rating) -> "tuple | None":
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
                return entry.seeker_id, entry.rating
        return None

    def remove(self, seeker_id):
        self._waiting = [e for e in self._waiting if e.seeker_id != seeker_id]


class RedisMatchmakingQueue:  # pragma: no cover - redis shell, exercised by running it
    """A queue shared by every Game Server, so a seeker on one is visible to
    matchmaking on another - held as a Redis hash, {seeker_id: rating}."""

    def __init__(self, url, config):
        import redis

        self._redis = redis.Redis.from_url(url, decode_responses=True)
        self._config = config

    def add(self, seeker_id, rating):
        self._redis.hset(_KEY, seeker_id, rating)

    def pop_match(self, rating):
        within = self._config.MATCHMAKING_ELO_RANGE
        for seeker_id, waiting_rating in self._redis.hgetall(_KEY).items():
            waiting_rating = int(waiting_rating)
            if abs(waiting_rating - rating) <= within:
                self._redis.hdel(_KEY, seeker_id)
                return seeker_id, waiting_rating
        return None

    def remove(self, seeker_id):
        self._redis.hdel(_KEY, seeker_id)
