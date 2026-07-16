import pytest

from board.board import Board
from config import settings
from rules.movement_strategy import MoveContext, MovementStrategy
from rules.piece_rules import (
    KingMovement, QueenMovement, RookMovement,
    BishopMovement, KnightMovement, PawnMovement,
    line_cells,
)
from rules.rule_registry import build_default_registry
from rules.rule_engine import RuleEngine, MovePlan


def context(board, color, start, end):
    return MoveContext(
        board=board,
        color=color,
        start=start,
        end=end,
        target_occupied=not board.is_empty(*end),
    )


def empty_board(width=8, height=8):
    return Board([["."] * width for _ in range(height)])


def make_engine(rows):
    board = Board(rows)
    registry = build_default_registry(settings)
    return RuleEngine(rule_registry=registry, config=settings), board


def test_king_moves_one_square_any_direction():
    board = empty_board()
    king = KingMovement()
    assert king.is_legal(1, 1, context(board, "w", (4, 4), (5, 5)))
    assert not king.is_legal(2, 0, context(board, "w", (4, 4), (6, 4)))


def test_rook_blocked_by_piece():
    board = empty_board()
    board.set(4, 6, "bP")
    rook = RookMovement()
    assert not rook.is_legal(0, 4, context(board, "w", (4, 4), (4, 8 - 1)))


def test_rook_clear_path():
    board = empty_board()
    rook = RookMovement()
    assert rook.is_legal(0, 3, context(board, "w", (4, 4), (4, 7)))


def test_rook_rejects_diagonal():
    board = empty_board()
    rook = RookMovement()
    assert not rook.is_legal(2, 2, context(board, "w", (4, 4), (6, 6)))


def test_bishop_requires_diagonal():
    board = empty_board()
    bishop = BishopMovement()
    assert bishop.is_legal(2, 2, context(board, "w", (2, 2), (4, 4)))
    assert not bishop.is_legal(2, 3, context(board, "w", (2, 2), (4, 5)))


def test_queen_moves_straight_or_diagonal():
    board = empty_board()
    queen = QueenMovement()
    assert queen.is_legal(0, 3, context(board, "w", (0, 0), (0, 3)))
    assert queen.is_legal(3, 3, context(board, "w", (0, 0), (3, 3)))
    assert not queen.is_legal(3, 1, context(board, "w", (0, 0), (3, 1)))


def test_knight_l_shape():
    board = empty_board()
    knight = KnightMovement()
    assert knight.is_legal(2, 1, context(board, "w", (0, 0), (2, 1)))
    assert not knight.is_legal(2, 2, context(board, "w", (0, 0), (2, 2)))


def test_pawn_single_step_forward():
    board = empty_board()
    pawn = PawnMovement({"w": -1, "b": 1})
    assert pawn.is_legal(-1, 0, context(board, "w", (6, 4), (5, 4)))


def test_pawn_double_step_requires_clear_path_and_start_row():
    # White's home rank on an 8x8 board is rank 2 (row 6 = height-2), one row
    # in from the back rank, as in standard chess.
    board = empty_board()
    pawn = PawnMovement({"w": -1, "b": 1})
    assert pawn.is_legal(-2, 0, context(board, "w", (6, 4), (4, 4)))

    board.set(5, 4, "bP")  # intermediate square blocked
    assert not pawn.is_legal(-2, 0, context(board, "w", (6, 4), (4, 4)))

    # A pawn on the back rank (row 7) is not a home-rank pawn, so it may not
    # double-step.
    assert not pawn.is_legal(-2, 0, context(empty_board(), "w", (7, 4), (5, 4)))


def test_pawn_diagonal_capture_only_when_occupied():
    board = empty_board()
    pawn = PawnMovement({"w": -1, "b": 1})
    assert not pawn.is_legal(-1, 1, context(board, "w", (6, 4), (5, 5)))

    board.set(5, 5, "bP")
    assert pawn.is_legal(-1, 1, context(board, "w", (6, 4), (5, 5)))


# ---------------------------------------------------------------------------
# Layer A: movement PATHS (pure geometry) and capture legality.
#
# `path` excludes the source, includes the destination, and reads no board
# occupancy: it is the stepping recipe the arbiter walks at run time. These
# tests pin the geometry per piece kind and the may_capture rule.
# ---------------------------------------------------------------------------

def test_rook_path_is_every_cell_up_to_and_including_end():
    rook = RookMovement()
    assert rook.path((4, 4), (4, 7)) == ((4, 5), (4, 6), (4, 7))
    assert rook.path((4, 4), (0, 4)) == ((3, 4), (2, 4), (1, 4), (0, 4))


def test_bishop_path_is_the_diagonal_line():
    bishop = BishopMovement()
    assert bishop.path((2, 2), (5, 5)) == ((3, 3), (4, 4), (5, 5))


def test_queen_path_straight_and_diagonal():
    queen = QueenMovement()
    assert queen.path((0, 0), (0, 3)) == ((0, 1), (0, 2), (0, 3))
    assert queen.path((0, 0), (3, 3)) == ((1, 1), (2, 2), (3, 3))


def test_pawn_double_step_path_is_mid_then_end():
    # G7 -> G5 (double advance for a white pawn moving up): the path is the
    # intermediate square then the destination, with no pawn-specific branch.
    pawn = PawnMovement({"w": -1, "b": 1})
    assert pawn.path((6, 6), (4, 6)) == ((5, 6), (4, 6))


def test_pawn_single_and_diagonal_paths_are_atomic_one_step():
    pawn = PawnMovement({"w": -1, "b": 1})
    assert pawn.path((6, 4), (5, 4)) == ((5, 4),)      # single straight step
    assert pawn.path((6, 4), (5, 5)) == ((5, 5),)      # diagonal capture step


def test_knight_and_king_paths_are_atomic_end_only():
    # Leapers inherit the atomic default: a single leap, no intermediate cells.
    assert KnightMovement().path((0, 0), (2, 1)) == ((2, 1),)
    assert KingMovement().path((4, 4), (5, 5)) == ((5, 5),)


def test_bare_strategy_subclass_inherits_atomic_default_path():
    # Any new piece kind gets the atomic (end,) default from the base class
    # without overriding path — proving King/Knight aren't special-cased.
    class DummyMovement(MovementStrategy):
        def is_legal(self, dr, dc, context):
            return True

    assert DummyMovement().path((1, 1), (3, 4)) == ((3, 4),)


def test_line_cells_matches_the_piece_path_geometry():
    # The shared geometry helper is the single source of the line: every
    # slider path is exactly line_cells of the same endpoints.
    assert line_cells((4, 4), (4, 7)) == RookMovement().path((4, 4), (4, 7))
    assert line_cells((6, 6), (4, 6)) == PawnMovement({"w": -1, "b": 1}).path((6, 6), (4, 6))


def test_may_capture_true_for_sliders_king_and_knight():
    # A clear-path move onto an enemy on the final cell: every non-pawn shape,
    # plus the pawn's diagonal, may take it.
    engine, board = make_engine([
        ["wR", ".", "bP", ".", ".", ".", ".", "."],
    ])
    assert engine.may_capture(board, (0, 0), (0, 2)) is True

    engine, board = make_engine([
        ["wB", ".", "."],
        [".", ".", "."],
        [".", ".", "bP"],
    ])
    assert engine.may_capture(board, (0, 0), (2, 2)) is True

    engine, board = make_engine([
        ["wQ", ".", "bP"],
    ])
    assert engine.may_capture(board, (0, 0), (0, 2)) is True

    engine, board = make_engine([
        ["wN", ".", "."],
        [".", ".", "."],
        [".", "bP", "."],
    ])
    assert engine.may_capture(board, (0, 0), (2, 1)) is True

    engine, board = make_engine([
        ["wK", "bP", "."],
    ])
    assert engine.may_capture(board, (0, 0), (0, 1)) is True


def test_may_capture_true_for_pawn_diagonal_false_for_pawn_straight():
    # The pawn shape carries the "no straight captures" rule: diagonal onto an
    # enemy is True, straight onto an enemy is False — knowledge stays in the
    # strategy, not the arbiter.
    engine, board = make_engine([
        [".", ".", "."],
        [".", "bP", "bP"],
        [".", "wP", "."],
    ])
    assert engine.may_capture(board, (2, 1), (1, 2)) is True     # diagonal
    assert engine.may_capture(board, (2, 1), (1, 1)) is False    # straight


def test_build_plan_bundles_path_and_capture_flag():
    # build_plan is the single entry point the engine calls: it returns the
    # frozen MovePlan pairing pure-geometry path with may_capture_final.
    engine, board = make_engine([
        ["wR", ".", "bP", ".", ".", ".", ".", "."],
    ])
    plan = engine.build_plan(board, (0, 0), (0, 2))
    assert isinstance(plan, MovePlan)
    assert plan.path == ((0, 1), (0, 2))
    assert plan.may_capture_final is True

    # A pawn stepping straight toward an enemy: path is geometric, but the plan
    # forbids the final capture (pawn-straight).
    engine, board = make_engine([
        [".", ".", "."],
        [".", "bP", "."],
        [".", "wP", "."],
    ])
    plan = engine.build_plan(board, (2, 1), (1, 1))
    assert plan.path == ((1, 1),)
    assert plan.may_capture_final is False
