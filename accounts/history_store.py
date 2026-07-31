"""Finished-game results, kept alongside accounts - same SQLite/PostgreSQL
split, for the same reason: simple today, one config change away from a
wide-column store at real scale (see docs/scale-architecture.md's Part 1).

Not the live game (that never touches a database - see GameEngine/Room); only
the one row a game leaves behind once GameEnded fires.
"""
from __future__ import annotations

import sqlite3
import threading
from typing import Protocol, runtime_checkable

_SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    winner   TEXT NOT NULL,
    loser    TEXT NOT NULL,
    reason   TEXT,
    ended_at INTEGER NOT NULL
)
"""


@runtime_checkable
class HistoryStore(Protocol):
    def record(self, winner, loser, reason, ended_at) -> None:
        ...

    def recent(self, username, limit) -> tuple:
        ...


def _as_result(row):
    winner, loser, reason, ended_at = row
    return {"winner": winner, "loser": loser, "reason": reason, "ended_at": ended_at}


class SqliteHistoryStore:
    def __init__(self, path):
        # Same reasoning as SqliteAccountStore: check_same_thread is off, and
        # a lock guards it instead, because /history is served by
        # ThreadingHTTPServer - a fresh thread per request sharing this one
        # connection - not by the game socket's single-threaded event loop.
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute(_SCHEMA)
            self._db.commit()

    def record(self, winner, loser, reason, ended_at):
        with self._lock:
            self._db.execute(
                "INSERT INTO games (winner, loser, reason, ended_at) VALUES (?, ?, ?, ?)",
                (winner, loser, reason, ended_at),
            )
            self._db.commit()

    def recent(self, username, limit):
        with self._lock:
            rows = self._db.execute(
                "SELECT winner, loser, reason, ended_at FROM games "
                "WHERE winner = ? OR loser = ? ORDER BY id DESC LIMIT ?",
                (username, username, limit),
            ).fetchall()
        return tuple(_as_result(row) for row in rows)


class PostgresHistoryStore:  # pragma: no cover - db shell, exercised by running it
    def __init__(self, url):
        import psycopg

        self._db = psycopg.connect(url, autocommit=True)
        self._lock = threading.Lock()  # one connection, many request threads - see above
        with self._lock:
            self._db.execute(_SCHEMA.replace("AUTOINCREMENT", "").replace(
                "INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY"
            ))

    def record(self, winner, loser, reason, ended_at):
        with self._lock:
            self._db.execute(
                "INSERT INTO games (winner, loser, reason, ended_at) VALUES (%s, %s, %s, %s)",
                (winner, loser, reason, ended_at),
            )

    def recent(self, username, limit):
        with self._lock:
            rows = self._db.execute(
                "SELECT winner, loser, reason, ended_at FROM games "
                "WHERE winner = %s OR loser = %s ORDER BY id DESC LIMIT %s",
                (username, username, limit),
            ).fetchall()
        return tuple(_as_result(row) for row in rows)
