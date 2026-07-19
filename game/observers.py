"""Observers of completed game events.

The engine announces each event to a list of observers rather than calling the
move log and the scoreboard by name, so a new consumer is a class here plus one
subscribe() call - the engine does not change.

Events carry their own context, including when they happened, so an observer
needs nothing but the event it is handed.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class GameObserver(ABC):
    """Receives game events as they occur."""

    @abstractmethod
    def on_event(self, event):
        """React to `event`. Every observer is sent every event, so one that
        cares about only some types filters here."""


class MoveRecorder(GameObserver):
    """Writes each completed move to the move log in written notation."""

    def __init__(self, move_log, notation):
        self._move_log = move_log
        self._notation = notation

    def on_event(self, event):
        text = self._notation.describe(
            event.piece, event.origin, event.destination, event.captured
        )
        self._move_log.record(event.piece[0], text, event.at_ms)


class CaptureScorer(GameObserver):
    """Credits the arriving color with the value of whatever it captured."""

    def __init__(self, scoreboard, piece_values):
        self._scoreboard = scoreboard
        self._piece_values = piece_values

    def on_event(self, event):
        if event.captured is None:
            return
        points = self._piece_values.get(event.captured[1], 0)
        self._scoreboard.award(event.piece[0], points)
