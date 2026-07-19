class BoardMapper:
    """Translates pixel coordinates into board cells.

    The only place that knows the cell size and where the board sits on the
    canvas, so the board and pieces stay free of pixels. Returns None for a
    click outside the board.

    `origin` is the board's top-left pixel. It defaults to (0, 0) for the text
    path, whose coordinates are already board-local; the graphical UI, which
    frames the board with panels and a gutter, injects the real offset.
    """

    def __init__(self, board, cell_size, origin=(0, 0)):
        self._board = board
        self._cell_size = cell_size
        self._origin_x, self._origin_y = origin

    def pixel_to_cell(self, x, y):
        local_x = x - self._origin_x
        local_y = y - self._origin_y
        if local_x < 0 or local_y < 0:
            return None
        row = local_y // self._cell_size
        col = local_x // self._cell_size
        if not self._board.in_bounds(row, col):
            return None
        return row, col
