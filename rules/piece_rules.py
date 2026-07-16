from rules.movement_strategy import MovementStrategy


def _shape_delta(dr, dc):
    return abs(dr), abs(dc)


def _unit_step(start, end):
    """The one-cell direction vector from start toward end along a straight or
    diagonal line. Each component is the sign of the corresponding delta
    (-1, 0 or +1), so this is the single place the "which way, one square"
    sign logic lives. Pure geometry; reads no occupancy.
    """
    sr, sc = start
    er, ec = end
    return (er > sr) - (er < sr), (ec > sc) - (ec < sc)


def line_cells(start, end):
    """Ordered cells from the square AFTER start up to and INCLUDING end,
    stepping one unit at a time along the straight/diagonal line between them.

    The source is EXCLUDED and the destination is INCLUDED, so a straight
    double-step yields (mid, end) and any single/diagonal step yields (end,).
    Pure geometry: it walks the line by direction alone and reads no board
    occupancy (occupancy is judged elsewhere, at run time).
    """
    dr, dc = _unit_step(start, end)
    r, c = start
    cells = []
    while (r, c) != end:
        r += dr
        c += dc
        cells.append((r, c))
    return tuple(cells)


def path_is_clear(board, start, end):
    """Shared sliding-piece helper: True if every square strictly between
    start and end is empty. Used by Rook, Bishop and Queen so the check is
    written once (DRY) instead of duplicated per piece.

    Reuses line_cells so the sign/step geometry lives ONLY in _unit_step:
    line_cells(start, end)[:-1] is exactly the cells strictly between the
    endpoints (drop the final cell, which is `end` itself).
    """
    return all(board.is_empty(*cell) for cell in line_cells(start, end)[:-1])


class KingMovement(MovementStrategy):
    def is_legal(self, dr, dc, context):
        r, c = _shape_delta(dr, dc)
        return max(r, c) == 1


class RookMovement(MovementStrategy):
    def is_legal(self, dr, dc, context):
        if not ((dr == 0) != (dc == 0)):
            return False
        return path_is_clear(context.board, context.start, context.end)

    def path(self, start, end):
        """The straight line of cells the rook steps through, excluding the
        source and including the destination. Pure geometry (no occupancy);
        the arbiter judges blockage cell-by-cell as it walks this path."""
        return line_cells(start, end)


class BishopMovement(MovementStrategy):
    def is_legal(self, dr, dc, context):
        r, c = _shape_delta(dr, dc)
        if not (r == c and r != 0):
            return False
        return path_is_clear(context.board, context.start, context.end)

    def path(self, start, end):
        """The diagonal line of cells the bishop steps through, excluding the
        source and including the destination. Pure geometry (no occupancy);
        the arbiter judges blockage cell-by-cell as it walks this path."""
        return line_cells(start, end)


class QueenMovement(MovementStrategy):
    def is_legal(self, dr, dc, context):
        r, c = _shape_delta(dr, dc)
        straight = (dr == 0) != (dc == 0)
        diagonal = r == c and r != 0
        if not (straight or diagonal):
            return False
        return path_is_clear(context.board, context.start, context.end)

    def path(self, start, end):
        """The straight-or-diagonal line of cells the queen steps through,
        excluding the source and including the destination. Pure geometry
        (no occupancy); the arbiter judges blockage as it walks this path."""
        return line_cells(start, end)


class KnightMovement(MovementStrategy):
    def is_legal(self, dr, dc, context):
        r, c = _shape_delta(dr, dc)
        return sorted([r, c]) == [1, 2]


class PawnMovement(MovementStrategy):
    """Pawn movement rule.

    The per-color advance direction is injected (so variants can flip it),
    while the rank a pawn may double-step from is derived from the board
    height rather than hardcoded - so a single instance works for any
    board size.
    """

    def __init__(self, directions):
        self._directions = directions

    def _home_row(self, direction, board):
        """The rank a pawn may double-step from: one row in front of the
        player's back rank, not the back rank itself (pawns start on the 2nd
        rank in standard chess, not the 1st). On an 8x8 board that is row 6
        for a color that moves up and row 1 for one that moves down. Derived
        from board height, so any board size works."""
        return 1 if direction > 0 else board.height - 2

    def is_legal(self, dr, dc, context):
        direction = self._directions[context.color]
        start_row = self._home_row(direction, context.board)
        sr, _sc = context.start

        if dc == 0:
            if dr == direction and not context.target_occupied:
                return True
            if sr == start_row and dr == 2 * direction and not context.target_occupied:
                mid_row = sr + direction
                return context.board.is_empty(mid_row, context.start[1])
            return False

        if abs(dc) == 1 and dr == direction and context.target_occupied:
            return True

        return False

    def path(self, start, end):
        """The cells the pawn steps through, excluding the source and including
        the destination. Pure geometry via the shared line walker: a straight
        double-step yields (mid, end), while a single or diagonal step yields
        (end,) with no pawn-specific branch. Occupancy is judged elsewhere."""
        return line_cells(start, end)
