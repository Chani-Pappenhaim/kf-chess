"""The game, reached over a network.

A remote proxy: it satisfies the same GameGateway contract the local engine
does, forwards every command to the server, and answers every question from the
last thing the server sent. The UI above it cannot tell the difference.

Two things follow from the server being the only authority. Time is not advanced
here - wait() does nothing, because the clock runs there. And a command is sent
and forgotten: what it did shows up in the next state, like everything else.
"""
from __future__ import annotations

from game.squares import cell_of, square_of
from protocol.commands import format_move
from protocol.messages import HintsRequest, JumpRequest, MoveRequest, encode


class NetworkGateway:
    def __init__(self, inbox, send):
        self._inbox = inbox
        self._send = send
        self._asked = None  # the square we last asked for hints about

    def render_model(self):
        return self._inbox.model()

    def wait(self, dt):
        """Nothing at all. The server owns the clock, and a client that
        advanced one of its own would drift into a game of its own."""

    def request_move(self, start, end):
        model = self._inbox.model()
        piece = model.piece_at(start)
        if piece is None:
            # The square emptied while it was selected. There is nothing to
            # name in the command, and nothing the server could move.
            return
        self._send(encode(MoveRequest(
            format_move(piece.token, start, end, model.height)
        )))

    def request_jump(self, cell):
        model = self._inbox.model()
        self._send(encode(JumpRequest(square_of(cell, model.height))))

    def legal_targets(self, cell):
        """The squares `cell` may move to, as far as we have been told.

        Asked afresh every frame by the view, so this asks the server only when
        the square changes - one message per selection, not one per frame. Until
        the answer lands there are no hints to draw, which costs a frame or two
        and nothing else.
        """
        model = self._inbox.model()
        square = square_of(cell, model.height)
        targets = self._inbox.hints(square)
        if targets is not None:
            return tuple(cell_of(target, model.height) for target in targets)
        if square != self._asked:
            self._asked = square
            self._send(encode(HintsRequest(square)))
        return ()
