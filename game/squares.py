"""How a square is written, and read back.

The one place the file/rank form of a square is defined, so written notation and
anything that has to parse a square agree by construction rather than by two
implementations happening to match.

Reading a square only decodes it. Whether the cell is on the board is the
board's question, and it already answers it.
"""
from __future__ import annotations

FIRST_FILE = "a"


class SquareError(ValueError):
    """Raised when text cannot be read as a file/rank square."""


def square_of(cell, board_height):
    """The written form of `cell`: (6, 4) on an 8-row board is 'e2'."""
    row, col = cell
    return f"{chr(ord(FIRST_FILE) + col)}{board_height - row}"


def cell_of(square, board_height):
    """The (row, col) that `square` names. The inverse of square_of."""
    if len(square) < 2:
        raise SquareError(square)
    try:
        rank = int(square[1:])
    except ValueError:
        raise SquareError(square)
    return board_height - rank, ord(square[0]) - ord(FIRST_FILE)
