"""The accounts, kept in PostgreSQL - the networked twin of SqliteAccountStore,
satisfying the same AccountStore contract so build_service can swap one for the
other without anything above it changing.
"""
from __future__ import annotations

import psycopg

from accounts.passwords import hash_password, verify
from accounts.store import Account

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    rating        INTEGER NOT NULL
)
"""


class PostgresAccountStore:  # pragma: no cover - db shell, exercised by running it
    def __init__(self, url, starting_rating):
        self._db = psycopg.connect(url, autocommit=True)
        self._starting_rating = starting_rating
        self._db.execute(_SCHEMA)

    def exists(self, username):
        row = self._db.execute(
            "SELECT 1 FROM accounts WHERE username = %s", (username,)
        ).fetchone()
        return row is not None

    def register(self, username, password):
        self._db.execute(
            "INSERT INTO accounts (username, password_hash, rating) VALUES (%s, %s, %s)",
            (username, hash_password(password), self._starting_rating),
        )
        return Account(username, self._starting_rating)

    def authenticate(self, username, password):
        row = self._db.execute(
            "SELECT password_hash, rating FROM accounts WHERE username = %s",
            (username,),
        ).fetchone()
        if row is None:
            return None
        password_hash, rating = row
        if not verify(password, password_hash):
            return None
        return Account(username, rating)

    def set_rating(self, username, rating):
        self._db.execute(
            "UPDATE accounts SET rating = %s WHERE username = %s", (rating, username)
        )
