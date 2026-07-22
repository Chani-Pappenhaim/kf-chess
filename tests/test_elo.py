from accounts.elo import expected, updated

K = 32


def test_equal_ratings_split_the_expectation_evenly():
    assert expected(1500, 1500) == 0.5


def test_a_higher_rating_is_expected_to_score_more():
    assert expected(1700, 1500) > 0.5
    assert expected(1500, 1700) < 0.5


def test_the_worked_example_from_the_spec():
    # Two equal 1500 players, K=32: the winner rises to 1516, the loser to 1484.
    assert updated(1500, 1500, K) == (1516, 1484)


def test_the_points_one_gains_are_the_points_the_other_loses():
    new_winner, new_loser = updated(1500, 1500, K)
    assert (new_winner - 1500) == (1500 - new_loser)


def test_beating_a_stronger_player_gains_more():
    small = updated(1500, 1500, K)[0] - 1500       # beating an equal
    large = updated(1500, 1900, K)[0] - 1500       # beating a stronger one
    assert large > small


def test_beating_a_weaker_player_gains_little():
    gain = updated(1900, 1500, K)[0] - 1900
    assert 0 < gain < 5


def test_ratings_come_back_as_whole_numbers():
    new_winner, new_loser = updated(1213, 1187, K)
    assert isinstance(new_winner, int) and isinstance(new_loser, int)
