import numpy as np

from config import settings
from ui.hud import Hud
from view.render_model import RenderModel
from game.move_log import MoveRecord


class _FakeCanvas:
    def __init__(self, width, height):
        self.img = np.zeros((height, width, 4), dtype=np.uint8)
        self.texts = []

    def put_text(self, txt, x, y, size, color, thickness):
        self.texts.append(txt)


def _canvas():
    return _FakeCanvas(settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)


def _model(**overrides):
    base = dict(pieces=(), width=8, height=8)
    base.update(overrides)
    return RenderModel(**base)


def test_hud_shows_the_title_and_both_scores():
    canvas = _canvas()
    Hud(settings).draw(canvas, _model(scores={"w": 5, "b": 3}))
    assert f"Name: {settings.PLAYER_NAME}" in canvas.texts
    assert "Score: 5" in canvas.texts  # white, below the board
    assert "Score: 3" in canvas.texts  # black, above the board


def test_hud_draws_coordinate_labels():
    canvas = _canvas()
    Hud(settings).draw(canvas, _model())
    assert "a" in canvas.texts and "h" in canvas.texts
    assert "1" in canvas.texts and "8" in canvas.texts


def test_hud_lists_each_colors_moves_in_its_panel():
    moves = (MoveRecord("w", "e2-e4", 4105), MoveRecord("b", "e7-e5", 9000))
    canvas = _canvas()
    Hud(settings).draw(canvas, _model(moves=moves))
    assert "e2-e4" in canvas.texts       # white panel
    assert "e7-e5" in canvas.texts       # black panel
    assert "00:04.105" in canvas.texts   # formatted move time


def test_hud_draws_game_over_banner():
    canvas = _canvas()
    Hud(settings).draw(canvas, _model(game_over=True))
    assert "GAME OVER" in canvas.texts


def test_hud_hides_banner_while_playing():
    canvas = _canvas()
    Hud(settings).draw(canvas, _model(game_over=False))
    assert "GAME OVER" not in canvas.texts
