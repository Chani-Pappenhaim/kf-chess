"""Subscribers that keep the game's own records.

Each holds its collaborators and exposes one method per event it takes, so the
bus is handed a bound method and nothing here inherits anything. Which event
reaches which method is decided once, in game/composition.py.
"""
from __future__ import annotations


class MoveRecorder:
    """Writes each completed move to the move log in written notation."""

    def __init__(self, move_log, notation):
        self._move_log = move_log
        self._notation = notation

    def record(self, event):
        text = self._notation.describe(
            event.piece, event.origin, event.destination, event.captured
        )
        self._move_log.record(event.piece[0], text, event.at_ms)


class CaptureScorer:
    """Credits the capturing colour with the value of what it took."""

    def __init__(self, scoreboard, piece_values):
        self._scoreboard = scoreboard
        self._piece_values = piece_values

    def award(self, event):
        points = self._piece_values.get(event.captured[1], 0)
        self._scoreboard.award(event.captor[0], points)
