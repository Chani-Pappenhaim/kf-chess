from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameSnapshot:
    """A frozen copy of the board handed to the renderer, so the view can never
    mutate the live model."""

    cells: tuple                   # tuple of tuples of tokens
    width: int
    height: int
    game_over: bool
    selected: tuple | None = None  # a cell to highlight, set only by whoever owns selection

    @classmethod
    def from_board(cls, board, game_over, selected=None):
        cells = tuple(tuple(row) for row in board.snapshot())
        return cls(
            cells=cells,
            width=board.width,
            height=board.height,
            game_over=game_over,
            selected=selected,
        )
