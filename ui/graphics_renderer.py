"""GraphicsRenderer - composes a RenderModel onto the board via Img.

The graphical counterpart of view.BoardRenderer: it consumes a read model (and
a sprite library) and produces a canvas Img, touching neither the engine nor
cv2. It maps each piece's domain state to a sprite (SpriteLibrary), picks the
current frame, and positions it - interpolating a piece that is mid-move so it
slides between cells. All drawing goes through Img.draw_on.
"""
from __future__ import annotations

from graphics.assets import solid
from graphics.img import Img

_HIGHLIGHT_COLOR = (0, 255, 0, 90)   # translucent green (BGRA) - selection
_RESTING_COLOR = (0, 0, 255, 110)    # translucent red (BGRA) - cooldown
_RESTING_STATES = ("short_rest", "long_rest")


class GraphicsRenderer:
    def __init__(self, sprite_library, cell_size):
        self._sprites = sprite_library
        self._cell = cell_size
        self._highlight = solid(cell_size, cell_size, _HIGHLIGHT_COLOR)

    def render(self, model, background, clock_ms=0, selected=None):
        """Draw the model over a copy of `background`, returning a new canvas.
        The selected cell is highlighted under the pieces; a piece in its rest
        cooldown gets a red veil that drains from the top down as the cooldown
        elapses, so the piece reads as unavailable and the shrinking veil shows
        how much rest is left."""
        canvas = Img()
        canvas.img = background.img.copy()
        if selected is not None:
            row, col = selected
            self._highlight.draw_on(canvas, col * self._cell, row * self._cell)
        for piece in model.pieces:
            animation = self._sprites.animation(piece.token, piece.state)
            frame = animation.frame_at(clock_ms)
            x, y = self._top_left(piece, frame)
            frame.draw_on(canvas, x, y)
            if piece.state in _RESTING_STATES:
                self._draw_rest_veil(canvas, piece)
        return canvas

    def _draw_rest_veil(self, canvas, piece):
        """Draw the red cooldown veil over a resting piece. It covers the whole
        cell when the rest begins and recedes downward as `cooldown_progress`
        rises, clearing from the top so the veil's lower edge stays pinned to
        the cell while its height shrinks to nothing when the cooldown ends."""
        remaining = 1.0 - piece.cooldown_progress
        height = int(round(remaining * self._cell))
        if height <= 0:
            return
        row, col = piece.cell
        top = row * self._cell + (self._cell - height)
        veil = solid(self._cell, height, _RESTING_COLOR)
        veil.draw_on(canvas, col * self._cell, top)

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
