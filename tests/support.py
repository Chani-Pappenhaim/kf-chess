"""Shared test doubles. Not a test module (no test_ prefix), so pytest skips it."""
from accounts.store import Account
from board.loaders import load_snapshot_board
from config import settings
from events.bus import EventBus
from game.composition import build_engine, build_registry


class FakeAccountStore:
    """An in-memory AccountStore, so server tests need no SQLite file. Password
    kept in the clear here because it is a fake - never do this for real."""

    def __init__(self, starting=1200):
        self._accounts = {}  # username -> [password, rating]
        self._starting = starting

    def exists(self, username):
        return username in self._accounts

    def register(self, username, password):
        self._accounts[username] = [password, self._starting]
        return Account(username, self._starting)

    def authenticate(self, username, password):
        record = self._accounts.get(username)
        if record is None or record[0] != password:
            return None
        return Account(username, record[1])

    def set_rating(self, username, rating):
        self._accounts[username][1] = rating


class FakeHistoryStore:
    """An in-memory HistoryStore, so server tests need no SQLite file."""

    def __init__(self):
        self._games = []       # newest first
        self._seen_ids = set()  # mirrors the real stores' UNIQUE(result_id) dedup

    def record(self, winner, loser, reason, ended_at, result_id=None):
        if result_id is not None:
            if result_id in self._seen_ids:
                return
            self._seen_ids.add(result_id)
        self._games.insert(0, {"winner": winner, "loser": loser, "reason": reason, "ended_at": ended_at})

    def recent(self, username, limit):
        mine = [g for g in self._games if username in (g["winner"], g["loser"])]
        return tuple(mine[:limit])


def engine_with(pieces, width=8, height=8):
    """A real, started engine on a board holding just `pieces` - (token, cell)
    pairs - for tests that need the actual rules rather than a fake."""
    registry = build_registry(settings)
    board = load_snapshot_board(pieces, width, height, registry, settings)
    engine = build_engine(board, registry, settings, EventBus())
    engine.start()
    return engine
