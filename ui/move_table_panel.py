"""MoveTablePanel - draws one player's move list (Time | Move) as a table.

A single view component instantiated twice - once for Black on the left, once
for White on the right - so the two side tables share all their drawing code
instead of duplicating it. Like GraphicsRenderer/Hud it only reads the render
model and draws through Img; it owns no game state. It selects its own color's
records from the model, formats each move's time, and lays out the rows inside a
bordered box, showing the most recent moves when they overflow the panel.
"""
from __future__ import annotations

from graphics.assets import solid

_BORDER = (150, 150, 150, 255)      # box outline (BGRA)
_FILL = (255, 255, 255, 255)        # panel background
_DIVIDER = (200, 200, 200, 255)     # header / column separators
_TEXT = (35, 35, 35, 255)           # near-black table text

_BORDER_PX = 2
_PAD = 14                           # left text inset
_TITLE_BASELINE = 30
_COL_HEADER_BASELINE = 62
_FIRST_ROW_BASELINE = 88
_ROW_STEP = 26
_MOVE_COL_DX = 108                  # x offset of the Move column from the Time column


def format_time(ms):
    """Render a millisecond clock as mm:ss.mmm (e.g. 4105 -> '00:04.105')."""
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


class MoveTablePanel:
    def __init__(self, title, color, x, y, width, height):
        self._title = title
        self._color = color
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        self._max_rows = (height - _FIRST_ROW_BASELINE) // _ROW_STEP
        # Pre-built bordered box (grey rect behind a slightly smaller white one).
        self._box = solid(width, height, _BORDER)
        self._inner = solid(width - 2 * _BORDER_PX, height - 2 * _BORDER_PX, _FILL)
        self._divider = solid(width, 1, _DIVIDER)

    def draw(self, canvas, model):
        self._box.draw_on(canvas, self._x, self._y)
        self._inner.draw_on(canvas, self._x + _BORDER_PX, self._y + _BORDER_PX)
        self._draw_headers(canvas)
        self._draw_rows(canvas, self._visible_records(model))

    def _visible_records(self, model):
        mine = [record for record in model.moves if record.color == self._color]
        return mine[-self._max_rows:]  # keep the most recent when they overflow

    def _draw_headers(self, canvas):
        cx = self._x + self._width // 2
        canvas.put_text(self._title, cx - 34, self._y + _TITLE_BASELINE, 0.8, _TEXT, 2)
        self._divider.draw_on(canvas, self._x, self._y + _TITLE_BASELINE + 10)
        time_x = self._x + _PAD
        canvas.put_text("Time", time_x, self._y + _COL_HEADER_BASELINE, 0.5, _TEXT, 1)
        canvas.put_text("Move", time_x + _MOVE_COL_DX, self._y + _COL_HEADER_BASELINE, 0.5, _TEXT, 1)
        self._divider.draw_on(canvas, self._x, self._y + _COL_HEADER_BASELINE + 8)

    def _draw_rows(self, canvas, records):
        time_x = self._x + _PAD
        move_x = time_x + _MOVE_COL_DX
        for i, record in enumerate(records):
            baseline = self._y + _FIRST_ROW_BASELINE + i * _ROW_STEP
            canvas.put_text(format_time(record.time_ms), time_x, baseline, 0.5, _TEXT, 1)
            canvas.put_text(record.notation, move_x, baseline, 0.5, _TEXT, 1)
