from board.board import Board


def make_board():
    return Board([["wK", ".", "bK"], [".", ".", "."]], ".")


def test_dimensions():
    board = make_board()
    assert board.width == 3
    assert board.height == 2


def test_get_set():
    board = make_board()
    board.set(1, 1, "wQ")
    assert board.get(1, 1) == "wQ"


def test_is_empty():
    board = make_board()
    assert board.is_empty(0, 1) is True
    assert board.is_empty(0, 0) is False


def test_in_bounds():
    board = make_board()
    assert board.in_bounds(0, 0) is True
    assert board.in_bounds(2, 0) is False
    assert board.in_bounds(0, -1) is False


def test_snapshot_is_a_copy():
    board = make_board()
    snap = board.snapshot()
    snap[0][0] = "bQ"
    assert board.get(0, 0) == "wK"


def test_empty_board_dimensions():
    board = Board([], ".")
    assert board.width == 0
    assert board.height == 0


def test_relocate_moves_token_and_clears_src():
    board = Board([[".", "."], [".", "."]], ".")
    board.set(0, 0, "wR")
    board.relocate((0, 0), (0, 1))
    assert board.get(0, 1) == "wR"
    assert board.is_empty(0, 0) is True


def test_relocate_overwrites_occupied_dst():
    board = Board([[".", "."], [".", "."]], ".")
    board.set(0, 0, "wR")
    board.set(0, 1, "bP")
    # relocate is dumb: it overwrites the enemy on dst and reports nothing
    # about the capture - the return value is None regardless.
    result = board.relocate((0, 0), (0, 1))
    assert result is None
    assert board.get(0, 1) == "wR"
    assert board.is_empty(0, 0) is True


def test_relocate_leaves_other_cells_untouched():
    board = Board([["wK", ".", "bK"], [".", "wR", "."]], ".")
    board.relocate((1, 1), (1, 2))
    assert board.get(1, 2) == "wR"
    assert board.is_empty(1, 1) is True
    # every cell not named in the relocate is exactly as before
    assert board.get(0, 0) == "wK"
    assert board.is_empty(0, 1) is True
    assert board.get(0, 2) == "bK"
    assert board.is_empty(1, 0) is True
