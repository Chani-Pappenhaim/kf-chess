import numpy as np

from config import settings
from ui.hud import Hud
from view.render_model import RenderModel, RenderPiece


class _FakeCanvas:
    def __init__(self, width, height):
        self.img = np.zeros((height, width, 4), dtype=np.uint8)
        self.texts = []

    def put_text(self, txt, x, y, size, color, thickness):
        self.texts.append(txt)


def _canvas():
    return _FakeCanvas(settings.BOARD_PX, settings.CANVAS_HEIGHT)


def test_hud_shows_material_counts_and_time():
    model = RenderModel(
        pieces=(
            RenderPiece("wP", (0, 0)),
            RenderPiece("bP", (1, 0)),
            RenderPiece("wK", (7, 4)),
        ),
        width=8,
        height=8,
        clock=5000,
    )
    canvas = _canvas()
    Hud(settings).draw(canvas, model)
    assert "White: 2" in canvas.texts
    assert "Black: 1" in canvas.texts
    assert "5s" in canvas.texts


def test_hud_draws_game_over_banner():
    canvas = _canvas()
    Hud(settings).draw(canvas, RenderModel(pieces=(), width=8, height=8, game_over=True))
    assert "GAME OVER" in canvas.texts


def test_hud_hides_banner_while_playing():
    canvas = _canvas()
    Hud(settings).draw(canvas, RenderModel(pieces=(), width=8, height=8, game_over=False))
    assert "GAME OVER" not in canvas.texts
