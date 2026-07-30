"""A login session as a contract, mapping a token to the account it belongs
to - issued once at login, resolved on every socket connect.
"""
from __future__ import annotations

import json
import secrets
from typing import Protocol, runtime_checkable

from accounts.store import Account

_TOKEN_BYTES = 18
_KEY_PREFIX = "token:"


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


class RedisTokenStore:  # pragma: no cover - redis shell, exercised by running it
    def __init__(self, url):
        import redis

        self._redis = redis.Redis.from_url(url, decode_responses=True)

    def issue(self, account):
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        payload = json.dumps({"username": account.username, "rating": account.rating})
        self._redis.set(_KEY_PREFIX + token, payload)
        return token

    def resolve(self, token):
        raw = self._redis.get(_KEY_PREFIX + token)
        if raw is None:
            return None
        data = json.loads(raw)
        return Account(data["username"], data["rating"])
