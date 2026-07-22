"""Which colour this client was given, once the server says.

Written on the socket thread when the welcome (or rejection) arrives, read on
the frame loop when the game is about to start. Set once and small, but the two
threads still meet here, so a lock guards the crossing.

The colour is the one thing a client cannot read off the game state: the state
names both players, but not which of them is you.
"""
from __future__ import annotations

import threading


class Identity:
    def __init__(self):
        self._lock = threading.Lock()
        self._color = None
        self._rejected = False

    def welcome(self, color):
        with self._lock:
            self._color = color

    def reject(self):
        with self._lock:
            self._rejected = True

    def color(self):
        """This client's colour, or None before the welcome arrives."""
        with self._lock:
            return self._color

    def rejected(self):
        """Whether the server turned this client away - the game was full."""
        with self._lock:
            return self._rejected
