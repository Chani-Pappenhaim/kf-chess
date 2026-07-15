"""GraphicsRenderer - composes a RenderModel onto the board via Img.

The graphical counterpart of view.BoardRenderer: it consumes a read model (and
a sprite library) and produces a canvas Img, touching neither the engine nor
cv2. It maps each piece's domain state to a sprite (SpriteLibrary), picks the
current frame, and positions it - sliding a piece that is mid-move between cells
and lifting a jumping piece along an arc so the hop is visible. All drawing goes
through Img.draw_on.
"""
from __future__ import annotations

from graphics.assets import solid
from graphics.img import Img

_HIGHLIGHT_COLOR = (0, 255, 0, 90)   # translucent green (BGRA) - selection
_RESTING_COLOR = (0, 0, 255, 110)    # translucent red (BGRA) - cooldown
_MOVE_HINT_COLOR = (60, 60, 60, 110)     # translucent dark dot - a reachable empty square
_CAPTURE_HINT_COLOR = (60, 60, 210, 120)  # translucent red tint - a capturable square
_RESTING_STATES = ("short_rest", "long_rest")
_HOP_HEIGHT_RATIO = 0.5              # peak jump lift, as a fraction of a cell
_MOVE_HINT_RATIO = 0.3              # move-hint dot size, as a fraction of a cell


class GraphicsRenderer:
    def __init__(self, sprite_library, cell_size, origin=(0, 0)):
        self._sprites = sprite_library
        self._cell = cell_size
        self._origin_x, self._origin_y = origin
        self._highlight = solid(cell_size, cell_size, _HIGHLIGHT_COLOR)
        self._hop_height = int(cell_size * _HOP_HEIGHT_RATIO)
        dot = int(cell_size * _MOVE_HINT_RATIO)
        self._move_hint = solid(dot, dot, _MOVE_HINT_COLOR)
        self._capture_hint = solid(cell_size, cell_size, _CAPTURE_HINT_COLOR)
        self._dot_offset = (cell_size - dot) // 2

    def render(self, model, background, clock_ms=0, selected=None, targets=()):
        """Draw the model over a copy of `background`, returning a new canvas.
        The selected cell is highlighted and its legal destinations are hinted
        (a dot on an empty square, a red tint on a square it can capture on),
        both under the pieces; a piece in its rest cooldown gets a red veil that
        drains from the top down as the cooldown elapses, so the piece reads as
        unavailable and the shrinking veil shows how much rest is left."""
        canvas = Img()
        canvas.img = background.img.copy()
        if selected is not None:
            row, col = selected
            self._highlight.draw_on(
                canvas, self._origin_x + col * self._cell, self._origin_y + row * self._cell
            )
        self._draw_targets(canvas, targets, model)
        for piece in model.pieces:
            animation = self._sprites.animation(piece.token, piece.state)
            frame = animation.frame_at(clock_ms)
            x, y = self._top_left(piece, frame)
            frame.draw_on(canvas, x, y)
            if piece.state in _RESTING_STATES:
                self._draw_rest_veil(canvas, piece)
        return canvas

    def _draw_targets(self, canvas, targets, model):
        """Hint each cell the selected piece may move to. A target that already
        holds a piece is a capture (red cell tint); an empty target gets a small
        centred dot. Occupancy is read from the model the renderer already has,
        so no rules leak into the view."""
        occupied = {piece.cell for piece in model.pieces}
        for row, col in targets:
            x = self._origin_x + col * self._cell
            y = self._origin_y + row * self._cell
            if (row, col) in occupied:
                self._capture_hint.draw_on(canvas, x, y)
            else:
                self._move_hint.draw_on(canvas, x + self._dot_offset, y + self._dot_offset)

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
        top = self._origin_y + row * self._cell + (self._cell - height)
        veil = solid(self._cell, height, _RESTING_COLOR)
        veil.draw_on(canvas, self._origin_x + col * self._cell, top)

    def _top_left(self, piece, frame):
        row, col = self._current_cell(piece)
        frame_h, frame_w = frame.img.shape[:2]
        x = int(self._origin_x + col * self._cell + (self._cell - frame_w) / 2)
        y = int(self._origin_y + row * self._cell + (self._cell - frame_h) / 2)
        if piece.state == "jump":
            # Lift the piece along the hop so the jump reads as a jump; clamp to
            # the top edge so a piece on the back rank never draws off-canvas.
            y = max(0, y - self._hop_arc(piece.progress))
        return x, y

    def _hop_arc(self, progress):
        """Vertical lift at `progress` of a hop: a parabola that is 0 at take-off
        and landing and peaks at `_hop_height` mid-flight (4p(1-p))."""
        return int(self._hop_height * 4 * progress * (1 - progress))

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
