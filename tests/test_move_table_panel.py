import numpy as np

from ui.move_table_panel import MoveTablePanel, format_time
from view.render_model import RenderModel
from game.move_log import MoveRecord


class _FakeCanvas:
    def __init__(self, width, height):
        self.img = np.zeros((height, width, 4), dtype=np.uint8)
        self.texts = []

    def put_text(self, txt, x, y, size, color, thickness):
        self.texts.append(txt)


def _model(moves):
    return RenderModel(pieces=(), width=8, height=8, moves=moves)


def test_format_time_is_mm_ss_millis():
    assert format_time(4105) == "00:04.105"
    assert format_time(65001) == "01:05.001"


def test_panel_draws_only_its_own_colors_moves():
    panel = MoveTablePanel("White", "w", 0, 0, 250, 400)
    canvas = _FakeCanvas(300, 400)
    panel.draw(canvas, _model((MoveRecord("w", "e2-e4", 1000), MoveRecord("b", "e7-e5", 2000))))
    assert "White" in canvas.texts
    assert "e2-e4" in canvas.texts
    assert "e7-e5" not in canvas.texts


def test_panel_keeps_the_most_recent_moves_when_they_overflow():
    panel = MoveTablePanel("White", "w", 0, 0, 250, 200)  # short panel -> few rows
    moves = tuple(MoveRecord("w", f"m{i}", i * 1000) for i in range(40))
    canvas = _FakeCanvas(300, 200)
    panel.draw(canvas, _model(moves))
    assert "m39" in canvas.texts     # newest is shown
    assert "m0" not in canvas.texts  # oldest has scrolled off
