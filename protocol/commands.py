"""The move command as it travels: 'WQe2e5'.

Colour, piece kind, from-square, to-square. Squares are written and read by
game.squares, so all this module decides is how the four parts are laid out.

Reading a command only decodes it. Whether the move is legal is the rules'
question, and whether the sender may move that colour is the server's - both
are asked later, of the board that is actually authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass

from game.squares import SquareError, cell_of, square_of
from protocol.errors import ProtocolError

PREFIX_LENGTH = 2  # colour + piece kind, ahead of the two squares


@dataclass(frozen=True)
class MoveCommand:
    """A move as its sender described it.

    `piece` is what the sender says it is moving. The server moves whatever its
    own board holds on `start`, so the token is context, never authority.
    """

    piece: str     # internal token, e.g. 'wQ'
    start: tuple
    end: tuple


def format_move(piece, start, end, board_height):
    """The wire form of a move: ('wQ', (6, 4), (3, 4)) on 8 rows is 'WQe2e5'."""
    return (
        piece[0].upper()
        + piece[1]
        + square_of(start, board_height)
        + square_of(end, board_height)
    )


def parse_move(text, board_height):
    """Read a wire move back into a MoveCommand.

    The squares are split where the second one's file letter begins rather than
    at a fixed offset, so a board deep enough to have two-digit ranks still
    parses.
    """
    first, second = _split_squares(text)
    try:
        start, end = cell_of(first, board_height), cell_of(second, board_height)
    except SquareError as error:
        raise ProtocolError(text) from error
    return MoveCommand(piece=text[0].lower() + text[1], start=start, end=end)


def _split_squares(text):
    squares = text[PREFIX_LENGTH:]
    for index in range(1, len(squares)):
        if squares[index].isalpha():
            return squares[:index], squares[index:]
    raise ProtocolError(text)
