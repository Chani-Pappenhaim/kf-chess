"""A login session as a contract, mapping a token to the account it belongs
to - issued once at login, resolved on every socket connect.
"""
from __future__ import annotations

import secrets
from typing import Protocol, runtime_checkable

from accounts.store import Account

_TOKEN_BYTES = 18


@runtime_checkable
class TokenStore(Protocol):
    def issue(self, account) -> str:
        ...

    def resolve(self, token) -> "Account | None":
        ...


class InMemoryTokenStore:
    def __init__(self):
        self._tokens = {}

    def issue(self, account):
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        self._tokens[token] = account
        return token

    def resolve(self, token):
        return self._tokens.get(token)
