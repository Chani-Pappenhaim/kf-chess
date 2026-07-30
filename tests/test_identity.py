from client.identity import Identity


def test_a_fresh_identity_knows_nothing_yet():
    identity = Identity()
    assert identity.logged_in() is False
    assert identity.rejected() is False
    assert identity.in_room() is False
    assert identity.color() is None
    assert identity.is_spectator() is False
    assert identity.no_opponent() is False
    assert identity.lost() is False


def test_a_welcome_marks_the_login_accepted():
    identity = Identity()
    identity.welcome()
    assert identity.logged_in() is True


def test_a_rejection_records_its_reason():
    identity = Identity()
    identity.reject("wrong password")
    assert identity.rejected() is True
    assert identity.rejection_reason() == "wrong password"


def test_entering_a_room_records_colour_room_and_role():
    identity = Identity()
    identity.entered("b", "7", True)
    assert identity.in_room() is True
    assert identity.color() == "b"
    assert identity.room_id() == "7"
    assert identity.is_spectator() is True


def test_a_failed_search_is_remembered_then_cleared_when_seeking_again():
    identity = Identity()
    identity.search_failed()
    assert identity.no_opponent() is True
    identity.seeking()
    assert identity.no_opponent() is False


def test_retry_forgets_both_a_failed_search_and_a_rejection():
    identity = Identity()
    identity.search_failed()
    identity.reject("no room with that id")
    identity.retry()
    assert identity.no_opponent() is False
    assert identity.rejected() is False


def test_a_redirect_carries_the_room_to_join():
    identity = Identity()
    assert identity.redirect_room_id() is None
    identity.redirected("7")
    assert identity.redirect_room_id() == "7"


def test_retry_also_forgets_a_redirect():
    identity = Identity()
    identity.redirected("7")
    identity.retry()
    assert identity.redirect_room_id() is None


def test_a_dropped_connection_carries_its_reason():
    identity = Identity()
    identity.connection_lost("connection lost")
    assert identity.lost() is True
    assert identity.loss_reason() == "connection lost"
