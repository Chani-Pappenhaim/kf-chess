"""The read-only view model for the graphical UI.

A richer sibling of GameSnapshot: it carries each piece's animation state and
any motion in progress, so the renderer can pick a sprite and interpolate a
sliding piece without touching the live model. A frozen DTO, like a server would
send a client.

Every piece is listed on the cell it occupies, so `pieces` holds exactly one
entry per occupied cell. Occupancy can therefore be read straight off the model
- including by a client that has no board of its own.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Animation states the model defines for itself. The two rest states are named
# in config instead, because the sprite loader reads them as folder names.
IDLE_STATE = "idle"
MOVE_STATE = "move"
JUMP_STATE = "jump"


@dataclass(frozen=True)
class RenderPiece:
    token: str          # internal board token, e.g. "wP"
    cell: tuple         # (row, col) the piece occupies on the board right now
    state: str = IDLE_STATE  # idle / move / jump / short_rest / long_rest
    target: tuple | None = None  # the cell it is stepping into, while in flight
    progress: float = 0.0        # 0..1: along cell -> target for a move, or
                                 # through the hop for a jump (0 when still)
    cooldown_progress: float = 0.0  # 0..1 elapsed while resting (drains the veil)


@dataclass(frozen=True)
class RenderModel:
    pieces: tuple
    width: int
    height: int
    game_over: bool = False
    clock: int = 0  # elapsed simulated time in ms (for the HUD)
    moves: tuple = ()  # MoveRecord per completed move, in order (both colors)
    scores: dict = field(default_factory=dict)  # {color: accumulated points}
    players: dict = field(default_factory=dict)  # {color: username}, empty locally

    def in_bounds(self, row, col):
        """Whether `(row, col)` is a square of this board at all - the question
        a click has to answer before it can mean anything."""
        return 0 <= row < self.height and 0 <= col < self.width

    def piece_at(self, cell):
        """The piece occupying `cell`, or None when the square is empty.

        Empty squares carry no entry of their own - there is nothing to draw and
        nothing to send - so absence is what an empty square looks like here.
        """
        for piece in self.pieces:
            if piece.cell == cell:
                return piece
        return None

    def selectable(self, cell):
        """Whether `cell` can be picked as a move source: a piece is there and
        it is free to act - not mid-move, not airborne, not resting.

        A question about state, not about the rules, so it is answerable from
        this model alone - by the view here, or by a client with no board.
        """
        if self.game_over:
            return False
        piece = self.piece_at(cell)
        return piece is not None and piece.state == IDLE_STATE
