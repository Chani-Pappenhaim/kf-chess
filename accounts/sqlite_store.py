"""The accounts, kept in SQLite.

The one place sqlite3 appears, the way cv2 stays in graphics/ and websockets in
the socket shells. It satisfies the AccountStore contract, so everything above it
talks to the contract and never to a database.

A password is hashed on the way in (see accounts.passwords) and only ever
verified, never read back. The starting rating is injected, so what "new player"
means is a setting, not a number buried here.
"""
from __future__ import annotations

import sqlite3

from accounts.passwords import hash_password, verify
from accounts.store import Account

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    rating        INTEGER NOT NULL
)
"""


class SqliteAccountStore:
    def __init__(self, path, starting_rating):
        # `path` may be ":memory:" for a throwaway database, which is what the
        # tests use. check_same_thread is off because the socket thread and the
        # game share one store; access is serialised by the single event loop.
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._starting_rating = starting_rating
        self._db.execute(_SCHEMA)
        self._db.commit()

    def exists(self, username):
        row = self._db.execute(
            "SELECT 1 FROM accounts WHERE username = ?", (username,)
        ).fetchone()
        return row is not None

    def register(self, username, password):
        self._db.execute(
            "INSERT INTO accounts (username, password_hash, rating) VALUES (?, ?, ?)",
            (username, hash_password(password), self._starting_rating),
        )
        self._db.commit()
        return Account(username, self._starting_rating)

    def authenticate(self, username, password):
        row = self._db.execute(
            "SELECT password_hash, rating FROM accounts WHERE username = ?",
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
            "UPDATE accounts SET rating = ? WHERE username = ?", (rating, username)
        )
        self._db.commit()
