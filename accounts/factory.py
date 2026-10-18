"""Which account/history store a given config actually means - shared by
`server/__main__.py` (the Game Server + API Gateway) and
`server/results_worker.py`, so "how DATABASE_URL(S) is interpreted" is
decided in exactly one place. Both processes must agree: if the worker used a
different rule than the Game Server, a rating written for a sharded user
could land in the wrong shard's row - or none at all.
"""
from __future__ import annotations

from accounts.history_store import PostgresHistoryStore, SqliteHistoryStore
from accounts.postgres_store import PostgresAccountStore
from accounts.sharded_store import ShardedAccountStore
from accounts.sqlite_store import SqliteAccountStore


def account_store_for(config):  # pragma: no cover - connects to a real database
    if config.DATABASE_URLS:
        return ShardedAccountStore([
            PostgresAccountStore(url, config.STARTING_RATING) for url in config.DATABASE_URLS
        ])
    if config.DATABASE_URL:
        return PostgresAccountStore(config.DATABASE_URL, config.STARTING_RATING)
    return SqliteAccountStore(config.ACCOUNTS_DB, config.STARTING_RATING)


def history_store_for(config):  # pragma: no cover - connects to a real database
    if config.DATABASE_URL:
        return PostgresHistoryStore(config.DATABASE_URL)
    return SqliteHistoryStore(config.HISTORY_DB)
