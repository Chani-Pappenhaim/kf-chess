"""Move notation strategies - turn a completed move into its written form.

A Strategy (like WinCondition / PromotionRule in rules.game_conditions) so the
written form of a move can be swapped without touching the engine that records
moves: coordinate notation is used now, and a standard-algebraic notation can be
added later as another MoveNotation with no other change.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class MoveNotation(ABC):
    """Formats a completed move into a display string."""

    @abstractmethod
    def describe(self, piece, origin, dest, captured):
        """Return the written form of a completed move.

        piece    - token at the destination, already promoted (e.g. 'wN')
        origin   - (row, col) the piece moved from
        dest     - (row, col) the piece moved to
        captured - the token captured on arrival, or None
        """


class CoordinateNotation(MoveNotation):
    """Full from-to coordinate notation: 'Ng1-f3', 'e2-e4', capture 'Rc3xc6'.

    Names both squares, so unlike standard algebraic notation it is always
    unambiguous and always correct - it never needs disambiguation or check
    detection (neither of which is well defined in this turn-less real-time
    variant). The piece-kind letter is shown for every piece except the pawn
    (kind 'P'), following chess convention. Rows map to ranks the way the board
    is drawn: row 0 is the top rank (board_height) down to the bottom rank 1.
    """

    def __init__(self, board_height):
        self._height = board_height

    def describe(self, piece, origin, dest, captured):
        letter = "" if piece[1] == "P" else piece[1]
        if origin == dest:
            # A stationary capture: a jumping piece intercepted a mover on its
            # own square without moving, so name the one square only ('Nxe4').
            return f"{letter}x{self._square(dest)}"
        separator = "x" if captured is not None else "-"
        return f"{letter}{self._square(origin)}{separator}{self._square(dest)}"

    def _square(self, cell):
        row, col = cell
        file = chr(ord("a") + col)
        rank = self._height - row
        return f"{file}{rank}"
