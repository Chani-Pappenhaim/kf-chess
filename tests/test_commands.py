import pytest

from protocol.commands import MoveCommand, ProtocolError, format_move, parse_move


def test_a_move_is_written_in_the_form_the_wire_expects():
    assert format_move("wQ", (6, 4), (3, 4), 8) == "WQe2e5"


def test_reading_a_move_recovers_its_parts():
    assert parse_move("WQe2e5", 8) == MoveCommand(piece="wQ", start=(6, 4), end=(3, 4))


def test_reading_a_move_inverts_writing_it():
    for piece, start, end in (("wQ", (6, 4), (3, 4)), ("bN", (0, 1), (2, 2))):
        text = format_move(piece, start, end, 8)
        assert parse_move(text, 8) == MoveCommand(piece, start, end)


def test_the_colour_travels_upper_case_and_comes_back_internal():
    # 'W' on the wire, 'w' in the board's own tokens.
    assert format_move("bR", (0, 0), (0, 1), 8).startswith("BR")
    assert parse_move("BRa8b8", 8).piece == "bR"


def test_squares_are_split_where_the_second_file_begins():
    # A board deep enough for two-digit ranks: the squares are no longer two
    # characters each, and a fixed offset would cut them in the wrong place.
    assert parse_move("WRa12a10", 12) == MoveCommand("wR", (0, 0), (2, 0))


def test_text_with_only_one_square_is_refused():
    with pytest.raises(ProtocolError):
        parse_move("WQe2", 8)


def test_a_square_that_cannot_be_read_is_refused():
    with pytest.raises(ProtocolError):
        parse_move("WQeXeY", 8)
