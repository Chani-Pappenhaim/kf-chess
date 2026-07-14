import play
from config import settings


def test_load_board_background_matches_logical_size():
    # Real end-to-end check that the board asset loads and is resized to the
    # logical board size (BOARD_PX square) that pieces will be positioned on.
    canvas = play.load_board_background(settings)
    height, width = canvas.img.shape[:2]
    assert (width, height) == (settings.BOARD_PX, settings.BOARD_PX)
