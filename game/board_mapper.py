class BoardMapper:
    """Translates pixel coordinates into board cells (Coordinate Adapter).

    Kept out of Board and Piece so the model stays free of pixels: only this
    adapter knows the cell size and where the board is drawn on the canvas.
    Returns None for a click that maps outside the board bounds.

    `origin` is the board's top-left pixel on the canvas. It defaults to (0, 0)
    so the text/VPL command path (whose `click x y` coordinates are board-local)
    is unaffected; the graphical UI, which frames the board with side panels and
    a coordinate gutter, injects the real offset so clicks still hit the cell
    under the cursor.
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
