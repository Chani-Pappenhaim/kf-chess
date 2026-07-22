"""Shared test doubles. Not a test module (no test_ prefix), so pytest skips it."""
from accounts.store import Account


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
