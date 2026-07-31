"""The accounts, kept in PostgreSQL - the networked twin of SqliteAccountStore,
satisfying the same AccountStore contract so build_service can swap one for the
other without anything above it changing.
"""
from __future__ import annotations

import threading

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
        # A load test caught this same connection genuinely shared across
        # ThreadingHTTPServer's request threads on the SQLite twin of this
        # class - psycopg's Connection is no more thread-safe than sqlite3's,
        # so the same lock applies here even though nothing has proven it yet.
        self._db = psycopg.connect(url, autocommit=True)
        self._lock = threading.Lock()
        self._starting_rating = starting_rating
        with self._lock:
            self._db.execute(_SCHEMA)

    def exists(self, username):
        with self._lock:
            row = self._db.execute(
                "SELECT 1 FROM accounts WHERE username = %s", (username,)
            ).fetchone()
        return row is not None

    def register(self, username, password):
        password_hash = hash_password(password)  # slow by design; kept off the lock
        with self._lock:
            self._db.execute(
                "INSERT INTO accounts (username, password_hash, rating) VALUES (%s, %s, %s)",
                (username, password_hash, self._starting_rating),
            )
        return Account(username, self._starting_rating)

    def authenticate(self, username, password):
        with self._lock:
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
        with self._lock:
            self._db.execute(
                "UPDATE accounts SET rating = %s WHERE username = %s", (rating, username)
            )
