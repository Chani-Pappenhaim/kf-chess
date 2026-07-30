"""What this client has been told about itself, across the two threads.

Written on the socket thread as the server's answers arrive, read on the frame
loop when a screen needs to know where it stands. Three things live here, none of
which a client can read off the game state:

- the login result (was the token accepted; was it refused),
- the room role (which room, which colour, whether a viewer),
- the connection (whether it dropped, and why).

The colour is the one a client cannot infer from the state - the state names both
players but not which is you - and it is not known until a room is entered, since
a full room makes the joiner a viewer. A lock guards every crossing.
"""
from __future__ import annotations

import threading


class Identity:
    def __init__(self):
        self._lock = threading.Lock()
        self._logged_in = False   # whether the server accepted the login
        self._rejection = None    # why the login was refused, if it was
        self._color = None        # this client's seat, once in a room
        self._room_id = None      # the room it is in
        self._spectator = False   # whether it entered as a viewer
        self._in_room = False     # whether a room has been entered at all
        self._no_opponent = False # whether the last Play search came up empty
        self._lost = None         # why the connection dropped, if it did

    # -- login ------------------------------------------------------------

    def welcome(self):
        with self._lock:
            self._logged_in = True

    def logged_in(self):
        """Whether the server accepted the token (the cue to leave the connecting
        screen for the home screen)."""
        with self._lock:
            return self._logged_in

    def reject(self, reason):
        with self._lock:
            self._rejection = reason

    def rejected(self):
        with self._lock:
            return self._rejection is not None

    def rejection_reason(self):
        with self._lock:
            return self._rejection

    # -- room -------------------------------------------------------------

    def entered(self, color, room_id, spectator):
        with self._lock:
            self._color = color
            self._room_id = room_id
            self._spectator = spectator
            self._in_room = True

    def in_room(self):
        """Whether the server has placed this client in a room yet."""
        with self._lock:
            return self._in_room

    def color(self):
        """This client's colour, or None on the home screen or as a viewer."""
        with self._lock:
            return self._color

    def room_id(self):
        with self._lock:
            return self._room_id

    def is_spectator(self):
        with self._lock:
            return self._spectator

    # -- matchmaking ------------------------------------------------------

    def search_failed(self):
        with self._lock:
            self._no_opponent = True

    def no_opponent(self):
        """Whether the last Play search timed out with no one to play."""
        with self._lock:
            return self._no_opponent

    def seeking(self):
        """Begin a fresh search, clearing any earlier 'none found'."""
        with self._lock:
            self._no_opponent = False

    def retry(self):
        """Back to the home screen: forget a search that came up empty or a room
        id that did not exist, so the next attempt starts clean."""
        with self._lock:
            self._no_opponent = False
            self._rejection = None

    # -- connection -------------------------------------------------------

    def connection_lost(self, reason):
        with self._lock:
            self._lost = reason

    def lost(self):
        with self._lock:
            return self._lost is not None

    def loss_reason(self):
        with self._lock:
            return self._lost
