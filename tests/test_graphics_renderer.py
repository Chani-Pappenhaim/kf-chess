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


def test_jumping_piece_is_lifted_along_the_hop():
    # cell 100, sprite 60 -> idle sits at y = 320 for row 3. Mid-hop (progress
    # 0.5) lifts it by the full hop height (0.5 * 100 = 50) -> y = 270.
    idle = _render(100, 60, RenderPiece("wP", (3, 3)))
    jumping = _render(100, 60, RenderPiece("wP", (3, 3), state="jump", progress=0.5))
    assert idle == [(320, 320)]
    assert jumping == [(320, 270)]  # same column, lifted upward


def test_jumping_piece_is_grounded_at_the_hop_ends():
    # At take-off/landing (progress 0 and 1) there is no lift: same as idle.
    assert _render(100, 60, RenderPiece("wP", (3, 3), state="jump", progress=0.0)) == [(320, 320)]
    assert _render(100, 60, RenderPiece("wP", (3, 3), state="jump", progress=1.0)) == [(320, 320)]


def test_resting_piece_is_veiled_red():
    cell = 100
    renderer = GraphicsRenderer(_FakeLibrary(_FakeFrame(60)), cell)
    piece = RenderPiece("wP", (1, 2), state="long_rest")
    model = RenderModel(pieces=(piece,), width=8, height=8)
    canvas = renderer.render(model, _FakeBackground(8 * cell))
    # cell (1, 2): the red veil raises the red channel (BGRA index 2) there,
    # and leaves the blue channel (index 0) untouched.
    assert canvas.img[150, 250][2] > 0
    assert canvas.img[150, 250][0] == 0


def test_rest_veil_drains_from_the_top_as_the_cooldown_elapses():
    cell = 100
    renderer = GraphicsRenderer(_FakeLibrary(_FakeFrame(60)), cell)
    # Half-elapsed cooldown on cell (0, 0): the veil should cover only the
    # bottom half of the cell (y >= 50), leaving the top half cleared.
    piece = RenderPiece("wP", (0, 0), state="long_rest", cooldown_progress=0.5)
    model = RenderModel(pieces=(piece,), width=8, height=8)
    canvas = renderer.render(model, _FakeBackground(8 * cell))
    assert canvas.img[25, 25][2] == 0   # top half cleared (no red)
    assert canvas.img[75, 25][2] > 0    # bottom half still veiled (red)


def test_rest_veil_is_gone_once_the_cooldown_completes():
    cell = 100
    renderer = GraphicsRenderer(_FakeLibrary(_FakeFrame(60)), cell)
    piece = RenderPiece("wP", (0, 0), state="long_rest", cooldown_progress=1.0)
    model = RenderModel(pieces=(piece,), width=8, height=8)
    canvas = renderer.render(model, _FakeBackground(8 * cell))
    assert canvas.img[75, 25][2] == 0   # nothing left to veil


def test_selection_highlight_tints_the_selected_cell():
    cell = 100
    renderer = GraphicsRenderer(_FakeLibrary(_FakeFrame(60)), cell)
    model = RenderModel(pieces=(), width=8, height=8)
    canvas = renderer.render(model, _FakeBackground(8 * cell), selected=(1, 2))
    # cell (1, 2): top-left pixel (x=200, y=100); the highlight raises green there.
    assert canvas.img[105, 205][1] > 0
    # a cell that was not selected stays untouched.
    assert canvas.img[5, 5][1] == 0
