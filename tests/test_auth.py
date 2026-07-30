from config import settings
from server.auth import account_for
from tests.support import FakeAccountStore


def test_a_new_username_is_registered():
    store = FakeAccountStore(settings.STARTING_RATING)
    account = account_for(store, "dana", "pw")
    assert account.username == "dana"
    assert store.exists("dana")


def test_a_returning_user_with_the_right_password_authenticates():
    store = FakeAccountStore(settings.STARTING_RATING)
    store.register("dana", "pw")
    assert account_for(store, "dana", "pw").username == "dana"


def test_a_returning_user_with_the_wrong_password_is_refused():
    store = FakeAccountStore(settings.STARTING_RATING)
    store.register("dana", "secret")
    assert account_for(store, "dana", "wrong") is None
