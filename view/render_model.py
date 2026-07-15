"""RenderModel - the read-only view model for the graphical UI.

Richer sibling of GameSnapshot: instead of just the logical grid it carries,
per piece, the animation/domain state and any in-flight motion, so the renderer
can pick the right sprite and interpolate a sliding piece without ever touching
the live Board or arbiter. Like GameSnapshot it is an immutable DTO - exactly
what a future networked server would serialise and send to a thin client.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderPiece:
    token: str          # internal board token, e.g. "wP"
    cell: tuple         # (row, col) logical destination cell
    state: str = "idle"  # idle / move / jump / short_rest / long_rest
    origin: tuple | None = None  # source cell while a move is in flight
    progress: float = 0.0        # 0..1: along origin -> cell for a move, or
                                 # through the hop for a jump (0 when still)
    cooldown_progress: float = 0.0  # 0..1 elapsed while resting (drains the veil)


@dataclass(frozen=True)
class RenderModel:
    pieces: tuple
    width: int
    height: int
    game_over: bool = False
    clock: int = 0  # elapsed simulated time in ms (for the HUD)
