"""GraphicsRenderer - composes a RenderModel onto the board via Img.

The graphical counterpart of view.BoardRenderer: it consumes a read model (and
a sprite library) and produces a canvas Img, touching neither the engine nor
cv2. It maps each piece's domain state to a sprite (SpriteLibrary), picks the
current frame, and positions it - interpolating a piece that is mid-move so it
slides between cells. All drawing goes through Img.draw_on.
"""
from __future__ import annotations

from graphics.img import Img


class GraphicsRenderer:
    def __init__(self, sprite_library, cell_size):
        self._sprites = sprite_library
        self._cell = cell_size

    def render(self, model, background, clock_ms=0):
        """Draw the model over a copy of `background`, returning a new canvas."""
        canvas = Img()
        canvas.img = background.img.copy()
        for piece in model.pieces:
            animation = self._sprites.animation(piece.token, piece.state)
            frame = animation.frame_at(clock_ms)
            x, y = self._top_left(piece, frame)
            frame.draw_on(canvas, x, y)
        return canvas

    def _top_left(self, piece, frame):
        row, col = self._current_cell(piece)
        frame_h, frame_w = frame.img.shape[:2]
        x = int(col * self._cell + (self._cell - frame_w) / 2)
        y = int(row * self._cell + (self._cell - frame_h) / 2)
        return x, y

    def _current_cell(self, piece):
        """The (possibly fractional) cell to draw at: the destination when
        still, or a point interpolated from origin while a move is in flight."""
        if piece.origin is None or piece.progress <= 0:
            return piece.cell
        (start_r, start_c), (end_r, end_c) = piece.origin, piece.cell
        return (
            start_r + (end_r - start_r) * piece.progress,
            start_c + (end_c - start_c) * piece.progress,
        )
