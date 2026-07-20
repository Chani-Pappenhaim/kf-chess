from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MoveResult:
    """The engine's answer to a command: accepted, or why it was refused.

    The refusal may come from the rules or from the engine's own guards; either
    way it is a code from rules.reasons.
    """

    is_accepted: bool
    reason: str


@dataclass(frozen=True)
class JumpEvent:
    """A piece has begun a jump. Announced by the engine the instant the command
    is accepted. It captures nothing, so it rides the same event handling as a
    completed move without ever ending the game."""

    piece: str
    cell: tuple
    at_ms: int = 0
    captured: str | None = None
