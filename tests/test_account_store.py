from accounts.store import Account, AccountStore
from accounts.sqlite_store import SqliteAccountStore

STARTING = 1200


def store():
    """A throwaway database in memory - a real SqliteAccountStore, no file."""
    return SqliteAccountStore(":memory:", STARTING)


def test_it_satisfies_the_account_store_contract():
    assert isinstance(store(), AccountStore)


def test_a_fresh_username_does_not_exist_yet():
    assert store().exists("dana") is False


def test_registering_creates_an_account_at_the_starting_rating():
    account = store().register("dana", "open sesame")
    assert account == Account("dana", STARTING)


def test_a_registered_username_then_exists():
    db = store()
    db.register("dana", "open sesame")
    assert db.exists("dana") is True


def test_the_right_password_authenticates():
    db = store()
    db.register("dana", "open sesame")
    assert db.authenticate("dana", "open sesame") == Account("dana", STARTING)


def test_a_wrong_password_does_not_authenticate():
    db = store()
    db.register("dana", "open sesame")
    assert db.authenticate("dana", "guess") is None


def test_an_unknown_username_does_not_authenticate():
    assert store().authenticate("nobody", "whatever") is None


def test_a_new_rating_is_kept_and_seen_on_the_next_login():
    db = store()
    db.register("dana", "open sesame")
    db.set_rating("dana", 1216)
    assert db.authenticate("dana", "open sesame").rating == 1216


def test_the_password_is_never_stored_in_the_clear():
    db = store()
    db.register("dana", "open sesame")
    stored_hash = db._db.execute(
        "SELECT password_hash FROM accounts WHERE username = ?", ("dana",)
    ).fetchone()[0]
    assert "open sesame" not in stored_hash


def test_two_players_keep_separate_accounts():
    db = store()
    db.register("dana", "one")
    db.register("yossi", "two")
    assert db.authenticate("dana", "one").username == "dana"
    assert db.authenticate("yossi", "two").username == "yossi"
    assert db.authenticate("dana", "two") is None
