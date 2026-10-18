"""How the computer picks a move from a Position.

A strategy is anything with `choose(position) -> (start, end) | None`, None
meaning "no move right now". It runs on a worker thread and sees only the
frozen Position, never the live game, so it may take its time.
"""
from __future__ import annotations

import logging
import random

_log = logging.getLogger("kfchess.bot")


class StrategyError(Exception):
    """A strategy could not come up with a move this time - throttled, or its
    answer was unusable. FallbackStrategy treats it like any other failure."""


class GreedyStrategy:
    """Takes the most valuable enemy piece any free piece can reach, and when
    nothing is in reach makes any legal move at random. Needs no network and
    never fails, which is what makes it the fallback behind smarter players."""

    def __init__(self, piece_values, rng=None):
        self._values = piece_values      # piece letter -> what taking it is worth
        self._rng = rng or random.Random()

    def choose(self, position):
        candidates = [
            (start, end)
            for start, targets in sorted(position.moves.items())
            for end in targets
        ]
        if not candidates:
            return None
        best = max(self._gain(position, move) for move in candidates)
        return self._rng.choice([move for move in candidates if self._gain(position, move) == best])

    def _gain(self, position, move):
        taken = position.captured_by(move[1])
        return self._values[taken[1]] if taken is not None else 0


class FallbackStrategy:
    """Asks `primary`; when it fails or has nothing to offer, asks `fallback`
    instead - so a network outage or a rate limit costs the computer some
    playing strength, never the game."""

    def __init__(self, primary, fallback, report=_log.warning):
        self._primary = primary
        self._fallback = fallback
        self._report = report

    def choose(self, position):
        try:
            move = self._primary.choose(position)
        # Deliberately broad: the primary is a network client whose library
        # may raise anything from a timeout to a quota error, and every one of
        # them means the same thing here - use the fallback this time.
        except Exception as error:
            self._report(f"computer falls back to {type(self._fallback).__name__}: {error!r}")
            move = None
        return move if move is not None else self._fallback.choose(position)
