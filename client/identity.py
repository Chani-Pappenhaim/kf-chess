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
        self._new_account = False  # whether the login just created the account
        self._rejection = None  # the reason string, once turned away

    def welcome(self, color, new_account=False):
        with self._lock:
            self._color = color
            self._new_account = new_account

    def new_account(self):
        """Whether the welcome said this login created a fresh account."""
        with self._lock:
            return self._new_account

    def reject(self, reason):
        with self._lock:
            self._rejection = reason

    def color(self):
        """This client's colour, or None before the welcome arrives."""
        with self._lock:
            return self._color

    def rejected(self):
        """Whether the server turned this client away (wrong password, or full)."""
        with self._lock:
            return self._rejection is not None

    def rejection_reason(self):
        """Why the server turned this client away, or None if it did not."""
        with self._lock:
            return self._rejection
