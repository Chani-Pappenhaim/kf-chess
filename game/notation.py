"""Turns a completed move into its written form.

Swappable, so a different notation is a new class here and nothing else.
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
    """Full from-to notation: 'Ng1-f3', 'e2-e4', capture 'Rc3xc6'.

    Naming both squares keeps it unambiguous without the disambiguation and
    check detection that standard algebraic needs - neither of which is well
    defined in a game without turns. Pawns carry no letter, by convention.
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
