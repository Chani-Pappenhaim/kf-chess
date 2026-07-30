from client.login import decide


def test_a_successful_login_returns_the_token_and_new_account_flag():
    assert decide(200, {"token": "abc", "new_account": True}) == ("abc", True)


def test_a_refused_login_returns_nothing():
    assert decide(401, {"reason": "wrong password"}) is None
