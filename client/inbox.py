"""What the server has told us so far.

The one place the two threads of a client meet: the socket thread writes what
arrives, the frame loop reads what to draw. Everything else on either side
touches only this, so there is exactly one thing to get right.

It holds no history. A state replaces the one before it, and a hints answer
replaces the one before it, because only the latest of either is ever wanted.
"""
from __future__ import annotations

import threading


class Inbox:
    def __init__(self):
        self._lock = threading.Lock()
        self._model = None
        self._hints = None  # (square, targets) of the last answer

    def receive_state(self, model):
        with self._lock:
            self._model = model

    def receive_hints(self, square, targets):
        with self._lock:
            self._hints = (square, targets)

    def model(self):
        """The last state received, or None before the first one arrives."""
        with self._lock:
            return self._model

    def hints(self, square):
        """The squares that piece may reach, or None if we have not been told
        about this square. None means 'no answer', which is not the same as an
        answer of 'nowhere'."""
        with self._lock:
            if self._hints is None or self._hints[0] != square:
                return None
            return self._hints[1]
