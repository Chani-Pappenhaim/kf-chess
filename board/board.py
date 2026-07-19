class Board:
    """The board every other layer works with: a grid of string tokens
    ('wK', 'bP', '.'), where a token is the color followed by the piece kind.

    This is the one internal representation. Other input formats are handled by
    loaders that convert them into a Board (see board/loaders.py), not by
    subclassing. The grid itself is private; callers go through the methods.
    """

    def __init__(self, rows, empty_token):
        self._cells = [list(row) for row in rows]
        self._empty_token = empty_token
        self._height = len(self._cells)
        self._width = len(self._cells[0]) if self._cells else 0

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    def in_bounds(self, row, col):
        return 0 <= row < self._height and 0 <= col < self._width

    def get(self, row, col):
        return self._cells[row][col]

    def set(self, row, col, value):
        self._cells[row][col] = value

    def is_empty(self, row, col):
        return self._cells[row][col] == self._empty_token

    def relocate(self, src, dst):
        """Move the token on `src` to `dst`, leaving `src` empty.

        Every piece that moves goes through here, so the pick-up-and-clear pair
        is written once. It overwrites whatever sits on `dst` without reading
        it: noticing a capture and applying promotion belong to the caller.
        Both cells are (row, col) tuples.
        """
        sr, sc = src
        dr, dc = dst
        self._cells[dr][dc] = self._cells[sr][sc]
        self._cells[sr][sc] = self._empty_token

    def snapshot(self):
        """A copy of the grid for rendering, so the caller cannot mutate the
        board through what it gets back."""
        return [row.copy() for row in self._cells]
