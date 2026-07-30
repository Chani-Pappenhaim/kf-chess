"""Deciding whose account a login belongs to - registering a new username, or
checking an existing one's password. Shared by the API Gateway's /login and the
tests, so the decision is tested without opening a port.
"""
from __future__ import annotations


def account_for(store, username, password):
    if not store.exists(username):
        return store.register(username, password)
    return store.authenticate(username, password)
