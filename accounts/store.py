"""Where accounts live, as a contract - not as a database.

The rest of the server depends on this Protocol, never on SQLite, so accounts
can be kept in a real database in play and in a plain dict in a test. An account
seen from the outside is a username and a rating; the password is not part of it,
because nothing outside verifying a login has any business with the password.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Account:
    """A player as everyone but the login sees them: who they are and how they
    are rated. Deliberately carries no password."""

    username: str
    rating: int


@runtime_checkable
class AccountStore(Protocol):
    def exists(self, username) -> bool:
        """Whether an account already exists for `username`."""
        ...

    def register(self, username, password) -> Account:
        """Create an account for `username` at the starting rating and return it.
        Called only when `exists` is false."""
        ...

    def authenticate(self, username, password) -> "Account | None":
        """The account when `password` matches the stored one, else None."""
        ...

    def set_rating(self, username, rating) -> None:
        """Record a new rating for `username`, after a game moves it."""
        ...
