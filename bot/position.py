"""What the computer sees: the game at one moment, frozen.

Captured on the game loop thread, then read on a worker thread while the game
moves on - so it is a plain immutable value, holding nothing that reaches back
into the live engine. A move chosen from it may be stale by the time it is
played; ComputerPlayer checks it against the live game first.
"""
from __future__ import annotations

from dataclasses import dataclass

from view.render_model import IDLE_STATE


@dataclass(frozen=True)
class Position:
    color: str          # the colour the computer plays
    width: int
    height: int
    occupants: dict     # {(row, col): token} for every occupied cell
    busy: tuple         # (token, cell, state) for each piece moving, jumping or resting
    moves: dict         # {start cell: (target cells, ...)} for the computer's free pieces

    def is_legal(self, start, end):
        """Whether moving `start` -> `end` was legal when this was captured."""
        return end in self.moves.get(start, ())

    def captured_by(self, end):
        """The enemy token a move landing on `end` would take, or None."""
        token = self.occupants.get(end)
        if token is None or token[0] == self.color:
            return None
        return token


def capture(engine, color):
    """The engine's current position as `color` sees it. Call on the loop
    thread: it reads the live engine."""
    model = engine.render_model()
    moves = {}
    for piece in model.pieces:
        if piece.token[0] != color or not model.selectable(piece.cell):
            continue
        targets = tuple(engine.legal_targets(piece.cell))
        if targets:
            moves[piece.cell] = targets
    return Position(
        color=color,
        width=model.width,
        height=model.height,
        occupants={piece.cell: piece.token for piece in model.pieces},
        busy=tuple(
            (piece.token, piece.cell, piece.state)
            for piece in model.pieces if piece.state != IDLE_STATE
        ),
        moves=moves,
    )
