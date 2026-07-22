"""Turns what a client says into commands on the authoritative engine.

The server trusts nothing it is told. A move names a piece and two squares, but
only the squares are used: the engine moves whatever its own board holds, and
refuses the move on its own rules. A client cannot move a piece that is not
there by claiming that it is.

A session also carries the colour its player was given, and acts only on that
colour's pieces. The engine stays turnless and colour-blind - both colours may
act in it at once - so whose move this is belongs here, at the seam between a
connection and the shared game, not in the engine.

Which message does what is a lookup, not a chain of tests, so a new message is
an entry here and a method beside it.
"""
from __future__ import annotations

from game.squares import cell_of, square_of
from protocol.commands import parse_move
from protocol.errors import ProtocolError
from protocol.messages import (
    HintsReply,
    HintsRequest,
    JumpRequest,
    MoveRequest,
    decode,
    encode,
)


class CommandHandler:
    def __init__(self, engine, board_height, send, color):
        self._engine = engine
        self._height = board_height
        self._send = send
        self._color = color
        self._actions = {
            MoveRequest: self._move,
            JumpRequest: self._jump,
            HintsRequest: self._hints,
        }

    @property
    def color(self):
        """The colour this session may act on - the seat it holds."""
        return self._color

    def handle(self, text):
        """Act on one line from a client.

        Raises ProtocolError on anything unreadable or on a message only a
        server is supposed to send, so the caller has one thing to catch and a
        bad line can never be mistaken for a legitimate command.
        """
        message = decode(text)
        action = self._actions.get(type(message))
        if action is None:
            raise ProtocolError(type(message).__name__)
        action(message)

    def _move(self, message):
        command = parse_move(message.command, self._height)
        if self._owns(command.start):
            self._engine.request_move(command.start, command.end)

    def _jump(self, message):
        cell = cell_of(message.square, self._height)
        if self._owns(cell):
            self._engine.request_jump(cell)

    def _hints(self, message):
        # Move hints are the one query only the server can answer, because the
        # rules live here and nowhere else. Only for this player's own pieces, so
        # the reply never reveals what the opponent could do.
        cell = cell_of(message.square, self._height)
        targets = ()
        if self._owns(cell):
            targets = tuple(
                square_of(target, self._height)
                for target in self._engine.legal_targets(cell)
            )
        self._send(encode(HintsReply(message.square, targets)))

    def _owns(self, cell):
        """Whether the piece on `cell` is this session's to move. Read from the
        board, never from what the client claimed, so a client cannot act on the
        other colour by naming one of its pieces."""
        piece = self._engine.render_model().piece_at(cell)
        return piece is not None and piece.token[0] == self._color
