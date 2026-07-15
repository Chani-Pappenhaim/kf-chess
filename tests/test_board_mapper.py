from board.board import Board
from game.board_mapper import BoardMapper


def _mapper(origin=(0, 0)):
    return BoardMapper(Board([[".", "."], [".", "."]]), 100, origin)


def test_maps_pixel_to_cell_without_offset():
    assert _mapper().pixel_to_cell(150, 50) == (0, 1)


def test_offset_is_subtracted_before_mapping():
    mapper = _mapper(origin=(200, 100))
    assert mapper.pixel_to_cell(200, 100) == (0, 0)   # the board origin itself
    assert mapper.pixel_to_cell(350, 250) == (1, 1)   # one cell right and down


def test_a_click_before_the_board_origin_is_outside():
    assert _mapper(origin=(200, 100)).pixel_to_cell(150, 90) is None


def test_a_click_past_the_board_is_outside():
    assert _mapper(origin=(200, 100)).pixel_to_cell(500, 100) is None  # col out of bounds
