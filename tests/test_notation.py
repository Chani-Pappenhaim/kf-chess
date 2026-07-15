from game.notation import CoordinateNotation


def notation(height=8):
    return CoordinateNotation(height)


def test_quiet_move_names_both_squares():
    # white knight g1 -> f3 on an 8x8 board: row 7 col 6 -> row 5 col 5
    assert notation().describe("wN", (7, 6), (5, 5), None) == "Ng1-f3"


def test_pawn_has_no_piece_letter():
    # white pawn e2 -> e4: row 6 col 4 -> row 4 col 4
    assert notation().describe("wP", (6, 4), (4, 4), None) == "e2-e4"


def test_capture_uses_x_separator():
    # rook c3 -> c6 capturing: row 5 col 2 -> row 2 col 2
    assert notation().describe("wR", (5, 2), (2, 2), "bP") == "Rc3xc6"


def test_rank_follows_board_height_so_row_zero_is_the_top_rank():
    # On a 3-row board, row 0 is rank 3 and row 2 is rank 1.
    assert notation(height=3).describe("wR", (2, 0), (0, 0), None) == "Ra1-a3"


def test_files_run_left_to_right_from_a():
    assert notation().describe("bQ", (0, 0), (0, 7), None) == "Qa8-h8"
