"""What the game announces on the bus.

The vocabulary only - no mechanism, no subscribers. Each event carries
everything a subscriber needs, including when it happened, so nobody has to
query the engine back.

One arrival can raise several of these. They are published from the specific to
the general, so a subscriber never sees a conclusion before its cause:

    MoveCompleted -> PieceCaptured (if it took a piece) -> GameEnded (if that
    ended the game)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameStarted:
    """The game is open to commands."""

    at_ms: int = 0


@dataclass(frozen=True)
class MoveCompleted:
    """A move settled on its destination.

    `captured` belongs here as well as on PieceCaptured because written
    notation marks a capture ('Rc3xc6'), and the two events answer different
    questions: what the move was, and what it cost.
    """

    piece: str
    origin: tuple
    destination: tuple
    captured: str | None
    at_ms: int


@dataclass(frozen=True)
class PieceCaptured:
    """A piece was taken off the board."""

    captor: str    # the token that took it, e.g. 'wR'
    captured: str  # the token taken, e.g. 'bN'
    cell: tuple    # where it was taken
    at_ms: int


@dataclass(frozen=True)
class JumpStarted:
    """A piece left the ground. Published the instant the command is accepted,
    since a jump has no arrival to wait for."""

    piece: str
    cell: tuple
    at_ms: int


@dataclass(frozen=True)
class GameEnded:
    """The win condition was met.

    `reason` says how the game ended: the default (None) is a win on the board -
    a king taken; a win without a capture (a player who left mid-game) carries a
    reason, so a subscriber can tell the two apart. Either way the winner is real.
    """

    winner: str    # the colour that won, 'w' or 'b'
    at_ms: int
    reason: str = None
