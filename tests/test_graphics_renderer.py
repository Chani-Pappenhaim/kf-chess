import numpy as np

from ui.graphics_renderer import GraphicsRenderer
from view.render_model import RenderModel, RenderPiece


class _FakeFrame:
    def __init__(self, size):
        self.img = np.zeros((size, size, 4), dtype=np.uint8)
        self.drawn_at = []

    def draw_on(self, canvas, x, y):
        self.drawn_at.append((x, y))


class _FakeLibrary:
    def __init__(self, frame):
        self._frame = frame

    def animation(self, token, state):
        return _FakeAnimation(self._frame)


class _FakeAnimation:
    def __init__(self, frame):
        self._frame = frame

    def frame_at(self, elapsed_ms):
        return self._frame


class _FakeBackground:
    def __init__(self, px):
        self.img = np.zeros((px, px, 4), dtype=np.uint8)


def _render(cell, frame_size, piece):
    frame = _FakeFrame(frame_size)
    renderer = GraphicsRenderer(_FakeLibrary(frame), cell)
    model = RenderModel(pieces=(piece,), width=8, height=8)
    renderer.render(model, _FakeBackground(8 * cell))
    return frame.drawn_at


def test_still_piece_is_centered_in_its_cell():
    # cell 100, sprite 60 -> centered with a (100-60)/2 = 20 px margin.
    assert _render(100, 60, RenderPiece("wP", (0, 0))) == [(20, 20)]


def test_moving_piece_is_interpolated_between_cells():
    # halfway from col 0 to col 2 -> col 1.0; full-cell sprite -> x = 100, y = 0.
    piece = RenderPiece("wP", (0, 2), state="move", origin=(0, 0), progress=0.5)
    assert _render(100, 100, piece) == [(100, 0)]


def test_selection_highlight_tints_the_selected_cell():
    cell = 100
    renderer = GraphicsRenderer(_FakeLibrary(_FakeFrame(60)), cell)
    model = RenderModel(pieces=(), width=8, height=8)
    canvas = renderer.render(model, _FakeBackground(8 * cell), selected=(1, 2))
    # cell (1, 2): top-left pixel (x=200, y=100); the highlight raises green there.
    assert canvas.img[105, 205][1] > 0
    # a cell that was not selected stays untouched.
    assert canvas.img[5, 5][1] == 0
