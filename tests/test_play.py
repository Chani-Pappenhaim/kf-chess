import play
from config import settings
from game.controller import Controller
from game.engine import GameEngine
from ui.composition import load_board_background, new_base_canvas


def test_build_game_returns_engine_and_wired_controller():
    engine, controller = play.build_game(settings)
    assert isinstance(engine, GameEngine)
    assert isinstance(controller, Controller)
    assert controller.selected is None


def test_load_board_background_matches_logical_size():
    # Real end-to-end check that the board asset loads and is resized to the
    # logical board size (BOARD_PX square) that pieces will be positioned on.
    canvas = load_board_background(settings)
    height, width = canvas.img.shape[:2]
    assert (width, height) == (settings.BOARD_PX, settings.BOARD_PX)


def test_new_base_canvas_spans_the_full_framed_window():
    canvas = new_base_canvas(settings)
    height, width = canvas.img.shape[:2]
    assert (width, height) == (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)
