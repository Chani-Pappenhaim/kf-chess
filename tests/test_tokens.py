from accounts.store import Account
from server.tokens import InMemoryTokenStore


def test_an_unknown_token_resolves_to_nothing():
    assert InMemoryTokenStore().resolve("nope") is None


def test_an_issued_token_resolves_to_its_account():
    tokens = InMemoryTokenStore()
    account = Account("dana", 1200)
    token = tokens.issue(account)
    assert tokens.resolve(token) == account


def test_two_issued_tokens_are_different():
    tokens = InMemoryTokenStore()
    account = Account("dana", 1200)
    assert tokens.issue(account) != tokens.issue(account)
