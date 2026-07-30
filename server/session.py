"""One connected client, from login to whichever game it ends up in.

A small state machine behind the socket's single `handle(text)`. It begins on
the home screen, where the only things it understands are "find me a game"
(Play), "open a room", and "join this room". The moment it enters a room it hands
the wheel to a CommandHandler bound to that room's game, and from then on every
line is a move, a jump, or a hint for that room and nothing else.

Departure is handled here too, because only the session knows which of the two
lives it was leading: a seeker still queued, or a member of a room.
"""
from __future__ import annotations

from protocol.errors import ProtocolError
from protocol.messages import (
    CreateRoom,
    JoinRoom,
    Rejected,
    SeekGame,
    decode,
    encode,
)
from server.handler import CommandHandler


class ClientSession:
    def __init__(self, account, lobby, matchmaker, send, config):
        self._account = account
        self._lobby = lobby
        self._matchmaker = matchmaker
        self._send = send
        self._config = config
        self._room = None
        self._color = None
        self._handler = None  # a CommandHandler once in a room
        self._home = {
            SeekGame: self._seek,
            CreateRoom: self._create,
            JoinRoom: self._join,
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
