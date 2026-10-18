"""The matchmaking queue as a contract, holding only an id and a rating per
seeker so it can move to a shared Redis. Wait time is aged per server, not
here.

Partitioned by region as well as by the ELO range each `pop_match` call
already applies: two seekers only pair within the same region, so matches
stay geographically close once a deployment actually spans more than one
(`config.REGION`, `server/matchmaking.py`). A single-region deployment - this
project's default - passes the same region everywhere and behaves exactly as
before.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

_KEY_PREFIX = "matchmaking:queue"

# Scans the region's hash for a rating within range and deletes it, in one
# atomic round-trip. Plain HGETALL-then-HDEL (two calls) has a check-then-act
# race: two Game Servers popping concurrently can both read the same seeker
# before either deletes it, double-matching one player into two rooms. A Lua
# script runs to completion on Redis's single execution thread with no other
# command interleaved, so this closes that race entirely - there is nothing
# for a second caller to observe between the read and the delete.
_POP_MATCH_SCRIPT = """
local entries = redis.call('HGETALL', KEYS[1])
local rating = tonumber(ARGV[1])
local within = tonumber(ARGV[2])
for i = 1, #entries, 2 do
    local seeker_id = entries[i]
    local waiting_rating = tonumber(entries[i + 1])
    if math.abs(waiting_rating - rating) <= within then
        redis.call('HDEL', KEYS[1], seeker_id)
        return {seeker_id, entries[i + 1]}
    end
end
return false
"""


@runtime_checkable
class MatchmakingQueue(Protocol):
    def add(self, seeker_id, rating, region) -> None:
        ...

    def pop_match(self, rating, region) -> "tuple | None":
        ...

    def remove(self, seeker_id, region) -> None:
        ...


class _Entry:
    __slots__ = ("seeker_id", "rating", "region")

    def __init__(self, seeker_id, rating, region):
        self.seeker_id = seeker_id
        self.rating = rating
        self.region = region


class InMemoryMatchmakingQueue:
    def __init__(self, config):
        self._config = config
        self._waiting = []

    def add(self, seeker_id, rating, region):
        self._waiting.append(_Entry(seeker_id, rating, region))

    def pop_match(self, rating, region):
        within = self._config.MATCHMAKING_ELO_RANGE
        for entry in self._waiting:
            if entry.region == region and abs(entry.rating - rating) <= within:
                self._waiting.remove(entry)
                return entry.seeker_id, entry.rating
        return None

    def remove(self, seeker_id, region):
        self._waiting = [
            e for e in self._waiting if not (e.seeker_id == seeker_id and e.region == region)
        ]


class RedisMatchmakingQueue:  # pragma: no cover - redis shell, exercised by running it
    """A queue shared by every Game Server, so a seeker on one is visible to
    matchmaking on another - held as one Redis hash per region,
    {seeker_id: rating}, so a scan for a match never crosses regions."""

    def __init__(self, url, config):
        import redis

        self._redis = redis.Redis.from_url(url, decode_responses=True)
        self._config = config
        self._pop_match = self._redis.register_script(_POP_MATCH_SCRIPT)

    def add(self, seeker_id, rating, region):
        self._redis.hset(self._key(region), seeker_id, rating)

    def pop_match(self, rating, region):
        result = self._pop_match(
            keys=[self._key(region)], args=[rating, self._config.MATCHMAKING_ELO_RANGE]
        )
        if not result:
            return None
        seeker_id, waiting_rating = result
        return seeker_id, int(waiting_rating)

    def remove(self, seeker_id, region):
        self._redis.hdel(self._key(region), seeker_id)

    def _key(self, region):
        return f"{_KEY_PREFIX}:{region}"
