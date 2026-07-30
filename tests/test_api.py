from config import settings
from server.api import handle_login
from server.tokens import InMemoryTokenStore
from tests.support import FakeAccountStore


def login(store, tokens, username, password):
    return handle_login(store, tokens, settings, {"username": username, "password": password})


def test_a_new_username_is_registered_and_given_a_token():
    status, payload = login(FakeAccountStore(settings.STARTING_RATING), InMemoryTokenStore(), "dana", "pw")
    assert status == 200
    assert payload["new_account"] is True
    assert payload["token"]


def test_a_returning_user_with_the_right_password_gets_a_token():
    store = FakeAccountStore(settings.STARTING_RATING)
    store.register("dana", "pw")
    status, payload = login(store, InMemoryTokenStore(), "dana", "pw")
    assert status == 200
    assert payload["new_account"] is False


def test_a_wrong_password_is_refused_with_no_token():
    store = FakeAccountStore(settings.STARTING_RATING)
    store.register("dana", "secret")
    status, payload = login(store, InMemoryTokenStore(), "dana", "wrong")
    assert status == 401
    assert payload == {"reason": settings.REJECT_WRONG_PASSWORD}


def test_the_issued_token_resolves_to_the_account():
    tokens = InMemoryTokenStore()
    _status, payload = login(FakeAccountStore(settings.STARTING_RATING), tokens, "dana", "pw")
    assert tokens.resolve(payload["token"]).username == "dana"
