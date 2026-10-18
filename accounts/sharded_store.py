"""Accounts spread across several database instances, so no single one holds
every user.

Satisfies the same `AccountStore` contract as `SqliteAccountStore`/
`PostgresAccountStore` (`accounts/store.py`), so `server/__main__.py` swaps a
single store for a sharded one with no change above it. Routes by
`hash(username) % len(shards)` - a plain modulo, not a hash *ring* like
`server/allocator.py::GameAllocator` uses for room placement. That is a
deliberate difference, not an oversight: a room's server can and does change
between games (rooms are short-lived, so the ring's "only reshuffle 1/K of
keys" property matters when the pool resizes live). An account's shard should
never move once assigned - moving it means migrating that user's row - so
sharding rarely, if ever, changes shard count at runtime here, and a plain
modulo is the simpler, equally correct tool for a key that's meant to be
fixed for the account's lifetime.
"""
from __future__ import annotations

import hashlib


class ShardedAccountStore:
    def __init__(self, shards):
        if not shards:
            raise ValueError("ShardedAccountStore needs at least one shard")
        self._shards = list(shards)

    def exists(self, username):
        return self._shard_for(username).exists(username)

    def register(self, username, password):
        return self._shard_for(username).register(username, password)

    def authenticate(self, username, password):
        return self._shard_for(username).authenticate(username, password)

    def set_rating(self, username, rating):
        self._shard_for(username).set_rating(username, rating)

    def _shard_for(self, username):
        # md5 (not the builtin hash()) so the mapping is stable across
        # processes and runs - Python's hash() is salted per-process for
        # strings, which would route the same username to a different shard
        # every time the server restarts.
        digest = hashlib.md5(username.encode("utf-8")).hexdigest()
        index = int(digest, 16) % len(self._shards)
        return self._shards[index]
