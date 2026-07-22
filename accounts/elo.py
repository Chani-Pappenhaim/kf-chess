"""ELO rating: how a result moves two players' ratings.

A pure calculation - no storage, no game, no notion of colour. Given the winner's
and loser's ratings it returns their new ones, so it can be tested on numbers
alone.

Only a decisive result is expressed, because that is all the game produces: a
game ends when a king is captured, so there is always a winner. A draw (S=0.5)
would be one more line, once a rule that can draw exists to call for it.
"""
from __future__ import annotations


def updated(winner_rating, loser_rating, k):
    """The winner's and loser's new ratings after the winner beats the loser.

    The winner scored 1 against an expected `expected(winner, loser)`, the loser
    0 against the complement, and each rating moves by k times that surprise.
    Rounded to whole points, the form ratings are kept and shown in.
    """
    expected_win = expected(winner_rating, loser_rating)
    new_winner = winner_rating + k * (1 - expected_win)
    new_loser = loser_rating + k * (0 - (1 - expected_win))
    return round(new_winner), round(new_loser)


def expected(rating, opponent_rating):
    """The probability `rating` scores against `opponent_rating`: 0.5 when equal,
    rising towards 1 as it outrates the opponent."""
    return 1 / (1 + 10 ** ((opponent_rating - rating) / 400))
