"""One connected client, from login to whichever game it ends up in.

A small state machine behind the socket's single `handle(text)`. It begins on
the home screen, where the only things it understands are "find me a game"
(Play), "open a room", "join this room", and "let me play the computer". The moment it enters a room it hands
the wheel to a CommandHandler bound to that room's game, and from then on every
line is a move, a jump, or a hint for that room and nothing else.

Departure is handled here too, because only the session knows which of the two
lives it was leading: a seeker still queued, or a member of a room.
"""
from __future__ import annotations

import random

from protocol.errors import ProtocolError
from protocol.messages import (
    CreateRoom,
    JoinRoom,
    PlayComputer,
    Rejected,
    SeekGame,
    decode,
    encode,
)
from server.handler import CommandHandler


class ClientSession:
    def __init__(self, account, lobby, matchmaker, send, config, rng=None):
        self._account = account
        self._lobby = lobby
        self._matchmaker = matchmaker
        self._send = send
        self._config = config
        self._rng = rng or random.Random()  # picks the colour when asked to
        self._room = None
        self._color = None
        self._handler = None  # a CommandHandler once in a room
        self._home = {
            SeekGame: self._seek,
            CreateRoom: self._create,
            JoinRoom: self._join,
            PlayComputer: self._play_computer,
        }

    @property
    def account(self):
        return self._account

    @property
    def color(self):
        """This session's seat colour, or None on the home screen or as a viewer."""
        return self._color

    def send(self, line):
        """One line out to this client - what a room broadcasts through."""
        self._send(line)

    def handle(self, text):
        """Act on one line. In a room it is a game command; on the home screen it
        is a lobby choice. Raises ProtocolError on anything else, so the socket
        has one thing to catch."""
        if self._room is not None:
            self._handler.handle(text)
            return
        message = decode(text)
        action = self._home.get(type(message))
        if action is None:
            raise ProtocolError(type(message).__name__)
        action(message)

    def enter_room(self, room, color, engine, board_height):
        """Bind to a room: from now on commands drive that room's game, on the
        colour it seated us (None for a viewer, whose commands own nothing)."""
        self._room = room
        self._color = color
        self._handler = CommandHandler(engine, board_height, self._send, color)

    def depart(self):
        """Clean up on disconnect: leave the room, or drop out of the queue."""
        if self._room is not None:
            self._room.leave(self)
        else:
            self._matchmaker.cancel(self)

    def _seek(self, _message):
        self._matchmaker.seek(self)

    def _create(self, message):
        self._lobby.create(message.room_id or None).join(self)

    def _join(self, message):
        room = self._lobby.room(message.room_id)
        if room is None:
            self._send(encode(Rejected(self._config.REJECT_NO_SUCH_ROOM)))
            return
        room.join(self)

    def _play_computer(self, message):
        """Open a room with the computer in the seat this player did not ask
        for, then join it - landing in the one seat left. The colour is drawn
        here, on the server, when the player leaves it to chance."""
        colors = self._config.COLORS
        color = message.color or self._rng.choice(colors)
        if color not in colors:
            self._send(encode(Rejected(self._config.REJECT_UNKNOWN_COLOR)))
            return
        room = self._lobby.create(message.room_id or None)
        room.add_computer(next(other for other in colors if other != color))
        room.join(self)
