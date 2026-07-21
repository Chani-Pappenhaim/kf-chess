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


@dataclass(frozen=True)
class RenderPiece:
    token: str          # internal board token, e.g. "wP"
    cell: tuple         # (row, col) the piece occupies on the board right now
    state: str = "idle"  # idle / move / jump / short_rest / long_rest
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
