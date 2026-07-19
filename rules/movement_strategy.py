from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from board.board import Board


@dataclass(frozen=True)
class MoveContext:
    """Everything a movement strategy needs to judge a move, bundled up.

    One immutable object rather than five loose parameters, so a strategy that
    needs more context does not change every signature along the way.
    """

    board: Board
    color: str
    start: tuple
    end: tuple
    target_occupied: bool


class MovementStrategy(ABC):
    """One piece kind's movement rule.

    A kind is added by implementing this interface and registering an instance
    with a PieceRuleRegistry; nothing else branches on the piece letter.
    """

    @abstractmethod
    def is_legal(self, dr: int, dc: int, context: MoveContext) -> bool:
        ...

    def path(self, start, end):
        """The cells this piece steps through to reach `end`, excluding the
        source and including the destination. Pure geometry - occupancy is
        judged later, as the piece actually walks it.

        The default is a single leap `(end,)` with no intermediate cells, which
        is what a king or a knight does. Sliding pieces override it with the
        full line between the endpoints.
        """
        return (end,)
