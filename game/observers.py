"""Observers of completed game events (Observer pattern).

The engine announces each event to a list of observers instead of calling the
move log, the scoreboard and anything else by name, so a new consumer - a sound
player, an animation trigger, a broadcaster feeding remote clients - is a class
here plus one subscribe() call at the composition root, and the engine does not
change.

Events are frozen DTOs that carry their own context (including when they
happened), so an observer needs nothing but the event it is handed, and the same
object can be serialised and sent over a network unchanged.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class GameObserver(ABC):
    """Receives game events as they occur."""

    @abstractmethod
    def on_event(self, event):
        """React to `event`. Observers that only care about some event types
        filter here; the engine sends every event to every observer."""


class MoveRecorder(GameObserver):
    """Writes each completed move to the move log in written notation.

    Owns the formatting step so the log stores finished text and the engine
    never touches notation.
    """

    def __init__(self, move_log, notation):
        self._move_log = move_log
        self._notation = notation

    def on_event(self, event):
        text = self._notation.describe(
            event.piece, event.origin, event.destination, event.captured
        )
        self._move_log.record(event.piece[0], text, event.at_ms)


class CaptureScorer(GameObserver):
    """Credits the arriving piece's color with the material value of whatever
    it captured. Events without a capture are ignored."""

    def __init__(self, scoreboard, piece_values):
        self._scoreboard = scoreboard
        self._piece_values = piece_values

    def on_event(self, event):
        if event.captured is None:
            return
        points = self._piece_values.get(event.captured[1], 0)
        self._scoreboard.award(event.piece[0], points)
