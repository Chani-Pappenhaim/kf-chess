from rules.movement_strategy import MovementStrategy


def _shape_delta(dr, dc):
    return abs(dr), abs(dc)


def _unit_step(start, end):
    """The one-cell direction vector from start toward end: each component is
    the sign of the corresponding delta (-1, 0 or +1)."""
    sr, sc = start
    er, ec = end
    return (er > sr) - (er < sr), (ec > sc) - (ec < sc)


def line_cells(start, end):
    """The cells on the straight line from start to end, including the end but not the start. Raises ValueError if the line is not straight or diagonal."""
    (start_row, start_col), (end_row, end_col) = start, end
    dr, dc = end_row - start_row, end_col - start_col
    if dr and dc and abs(dr) != abs(dc):
        raise ValueError(f"{start} -> {end} is neither straight nor diagonal")
    step_row, step_col = _unit_step(start, end)
    return tuple(
        (start_row + step_row * step, start_col + step_col * step)
        for step in range(1, max(abs(dr), abs(dc)) + 1)
    )


def path_is_clear(board, start, end):
    """True if every square strictly between start and end is empty.

    Dropping the last cell of the line leaves exactly the squares in between -
    the destination is excluded, since an enemy there is a capture, not a block.
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
        return line_cells(start, end)


class BishopMovement(MovementStrategy):
    def is_legal(self, dr, dc, context):
        r, c = _shape_delta(dr, dc)
        if not (r == c and r != 0):
            return False
        return path_is_clear(context.board, context.start, context.end)

    def path(self, start, end):
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
        return line_cells(start, end)


class KnightMovement(MovementStrategy):
    def is_legal(self, dr, dc, context):
        r, c = _shape_delta(dr, dc)
        return sorted([r, c]) == [1, 2]


class PawnMovement(MovementStrategy):
    """Pawn movement: one step forward, two from the home rank, captures only
    on the diagonal.

    The per-color advance direction is injected, and the home rank is derived
    from the board height, so one instance works on any board size.
    """

    def __init__(self, directions):
        self._directions = directions

    def _home_row(self, direction, board):
        """The rank a pawn may double-step from: one row in front of that
        color's back rank, derived from the board height rather than fixed."""
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
        # The shared line walker already gives (mid, end) for a double-step and
        # (end,) for a single or diagonal one - no pawn-specific branch needed.
        return line_cells(start, end)
