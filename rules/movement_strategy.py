from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from board.board import Board


@dataclass(frozen=True)
class MoveContext:
    """Everything a movement strategy needs to judge a move, bundled up.

    Keeping this as one immutable object (instead of passing five loose
    parameters around) is what lets new piece kinds be registered without
    changing every call site.
    """

    board: Board
    color: str
    start: tuple
    end: tuple
    target_occupied: bool


class MovementStrategy(ABC):
    """A single piece kind's movement rule (Strategy pattern).

    New piece kinds - including custom, non-standard ones - are supported
    simply by implementing this interface and registering an instance with
    a PieceRuleRegistry. No engine or parser code needs to change.
    """

    @abstractmethod
    def is_legal(self, dr: int, dc: int, context: MoveContext) -> bool:
        ...

    def path(self, start, end):
        """The cells this piece steps through to reach `end`, excluding the
        source and including the destination. Pure geometry: it never reads
        board occupancy (that is judged at run time as the arbiter walks it).

        The atomic default is a single leap `(end,)` — no intermediate cells —
        which is exactly right for King and Knight (a knight's L-jump has no
        squares to pass through). Sliding pieces (Rook/Bishop/Queen/Pawn)
        override this to return the full line between the endpoints.
        """
        return (end,)
