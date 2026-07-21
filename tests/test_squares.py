import pytest

from game.squares import SquareError, cell_of, square_of


def test_the_bottom_left_square_is_a1_on_an_eight_row_board():
    assert square_of((7, 0), 8) == "a1"


def test_the_top_right_square_is_h8_on_an_eight_row_board():
    assert square_of((0, 7), 8) == "h8"


def test_reading_a_square_inverts_writing_it():
    for cell in ((0, 0), (7, 7), (6, 4), (3, 2)):
        assert cell_of(square_of(cell, 8), 8) == cell


def test_the_rank_is_measured_from_the_board_height():
    # The same cell is written differently on a shorter board, which is why the
    # height is passed in rather than assumed to be eight.
    assert square_of((0, 0), 3) == "a3"
    assert cell_of("a3", 3) == (0, 0)


def test_a_two_digit_rank_is_read_whole():
    assert cell_of("c12", 12) == (0, 2)


def test_text_too_short_to_be_a_square_is_refused():
    with pytest.raises(SquareError):
        cell_of("e", 8)


def test_a_rank_that_is_not_a_number_is_refused():
    with pytest.raises(SquareError):
        cell_of("ee", 8)


def test_a_square_off_the_board_is_decoded_not_refused():
    # Decoding says what the text names; whether that cell exists is the
    # board's question, and it is asked later.
    assert cell_of("a99", 8) == (-91, 0)
