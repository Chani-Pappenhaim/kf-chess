from accounts.passwords import hash_password, verify


def test_the_right_password_verifies():
    stored = hash_password("open sesame")
    assert verify("open sesame", stored) is True


def test_a_wrong_password_does_not():
    stored = hash_password("open sesame")
    assert verify("guess", stored) is False


def test_the_password_is_not_stored_in_the_clear():
    stored = hash_password("open sesame")
    assert "open sesame" not in stored


def test_the_same_password_hashes_differently_each_time():
    # A fresh salt per hash, so two accounts with the same password do not share
    # a stored value - and both still verify.
    first = hash_password("open sesame")
    second = hash_password("open sesame")
    assert first != second
    assert verify("open sesame", first) and verify("open sesame", second)


def test_a_malformed_stored_value_fails_rather_than_raises():
    # Junk in the store must not crash a login; it just does not verify.
    assert verify("anything", "not-a-valid-hash") is False
    assert verify("anything", "") is False
    assert verify("anything", "xyz$zzz") is False  # non-hex halves
