from game.scoreboard import Scoreboard


def test_scores_start_at_zero_for_every_color():
    board = Scoreboard(("w", "b"))
    assert board.score("w") == 0
    assert board.score("b") == 0
    assert board.as_dict() == {"w": 0, "b": 0}


def test_awarded_points_accumulate_per_color():
    board = Scoreboard(("w", "b"))
    board.award("w", 3)
    board.award("w", 5)
    board.award("b", 1)

    assert board.score("w") == 8
    assert board.score("b") == 1


def test_as_dict_is_a_copy_and_does_not_leak_internal_state():
    board = Scoreboard(("w", "b"))
    snapshot = board.as_dict()
    snapshot["w"] = 999
    assert board.score("w") == 0
