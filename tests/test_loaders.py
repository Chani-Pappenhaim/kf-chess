import pytest

from config import settings
from board.board import Board
from board.loaders import load_text_board, load_csv_board, load_snapshot_board, BoardParseError
from rules.rule_registry import build_default_registry


@pytest.fixture
def registry():
    return build_default_registry(settings)


def test_load_text_board_builds_a_board(registry):
    board = load_text_board(["wK . bK"], registry, settings)
    assert isinstance(board, Board)
    assert board.get(0, 0) == "wK"
    assert board.is_empty(0, 1)


def test_load_text_board_rejects_unknown_token(registry):
    with pytest.raises(BoardParseError):
        load_text_board(["wX . bK"], registry, settings)


def test_load_text_board_rejects_row_width_mismatch(registry):
    with pytest.raises(BoardParseError):
        load_text_board(["wK . bK", "wK ."], registry, settings)


def test_load_text_board_skips_blank_lines(registry):
    board = load_text_board(["wK . bK", "", "  "], registry, settings)
    assert board.height == 1


def test_load_csv_board_translates_ctd26_codes(registry):
    # CTD26 uses KIND+COLOR ("PW", "KB"); the loader translates to the internal
    # color+kind tokens ("wP", "bK") so no engine code sees the external format.
    board = load_csv_board(["PW,,KB"], registry, settings)
    assert board.get(0, 0) == "wP"
    assert board.is_empty(0, 1)
    assert board.get(0, 2) == "bK"


def test_load_csv_board_maps_empty_field_to_empty_cell(registry):
    board = load_csv_board([",,,,,,,"], registry, settings)
    assert board.width == 8
    assert all(board.is_empty(0, c) for c in range(8))


def test_load_csv_board_rejects_unknown_token(registry):
    with pytest.raises(BoardParseError):
        load_csv_board(["PW,XW"], registry, settings)  # X is not a piece kind


def test_load_csv_board_rejects_malformed_code(registry):
    with pytest.raises(BoardParseError):
        load_csv_board(["P"], registry, settings)  # code must be KIND+COLOR


def test_load_csv_board_rejects_row_width_mismatch(registry):
    with pytest.raises(BoardParseError):
        load_csv_board(["PW,PB", "PW"], registry, settings)


def test_load_csv_board_skips_blank_lines(registry):
    board = load_csv_board(["PW,PB", "", "   "], registry, settings)
    assert board.height == 1


def test_load_snapshot_board_places_each_piece_at_its_cell(registry):
    board = load_snapshot_board([("wK", (0, 0)), ("bK", (0, 2))], 3, 1, registry, settings)
    assert board.get(0, 0) == "wK"
    assert board.is_empty(0, 1)
    assert board.get(0, 2) == "bK"


def test_load_snapshot_board_rejects_unknown_token(registry):
    with pytest.raises(BoardParseError):
        load_snapshot_board([("wX", (0, 0))], 1, 1, registry, settings)
