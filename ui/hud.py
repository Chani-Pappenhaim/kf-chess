"""Hud - the board "chrome": everything drawn around the board itself.

A view component like GraphicsRenderer: it reads the render model and draws onto
the canvas through Img, touching neither the engine nor cv2. It owns the title
strip ("Name: ..."), the per-side score strips (from the model's scores), the
a-h / 1-8 coordinate labels in the gutter around the board, and the game-over
banner - and it composes two MoveTablePanels (Black on the left, White on the
right) so the move-list drawing lives in one reusable place. The board and its
pieces are drawn separately by GraphicsRenderer; the Hud only frames them.
"""
from __future__ import annotations

from graphics.assets import solid
from ui.move_table_panel import MoveTablePanel

_TEXT = (35, 35, 35, 255)          # near-black title / score / label text (BGRA)
_BANNER_BG = (0, 0, 0, 180)        # translucent black
_BANNER_TEXT = (0, 0, 255, 255)    # red
_APPROX_CHAR_PX = 10               # rough per-character width, for centering text


class Hud:
    def __init__(self, config):
        self._bx = config.BOARD_ORIGIN_X
        self._by = config.BOARD_ORIGIN_Y
        self._cell = config.CELL_SIZE
        self._board_px = config.BOARD_PX
        self._gutter = config.COORD_GUTTER
        self._name = config.PLAYER_NAME
        self._title_baseline = config.TITLE_HEIGHT - 16
        self._top_score_baseline = config.TITLE_HEIGHT + config.SCORE_HEIGHT - 12
        self._bottom_score_baseline = (
            self._by + self._board_px + self._gutter + config.SCORE_HEIGHT - 12
        )
        self._banner = solid(self._board_px, 90, _BANNER_BG)
        # Black is at the top of the board (left panel); White at the bottom (right).
        self._black_panel = MoveTablePanel(
            "Black", "b", 10, self._by, config.PANEL_WIDTH - 20, self._board_px
        )
        self._white_panel = MoveTablePanel(
            "White", "w", self._bx + self._board_px + self._gutter + 10, self._by,
            config.PANEL_WIDTH - 20, self._board_px,
        )

    def draw(self, canvas, model):
        self._draw_title(canvas)
        self._draw_scores(canvas, model)
        self._draw_coordinates(canvas, model)
        self._black_panel.draw(canvas, model)
        self._white_panel.draw(canvas, model)
        if model.game_over:
            self._draw_game_over(canvas)

    def _draw_title(self, canvas):
        text = f"Name: {self._name}"
        canvas.put_text(text, self._centered(text), self._title_baseline, 0.8, _TEXT, 2)

    def _draw_scores(self, canvas, model):
        # Each player's score sits on their side of the board: Black above, White
        # below. as_dict on a fresh scoreboard is {'w': 0, 'b': 0}.
        black = f"Score: {model.scores.get('b', 0)}"
        white = f"Score: {model.scores.get('w', 0)}"
        canvas.put_text(black, self._centered(black), self._top_score_baseline, 0.9, _TEXT, 2)
        canvas.put_text(white, self._centered(white), self._bottom_score_baseline, 0.9, _TEXT, 2)

    def _draw_coordinates(self, canvas, model):
        """The a-h files above and below the board, and the ranks down each side
        (row 0 is the top rank = model.height, matching the coordinate notation)."""
        for col in range(model.width):
            file = chr(ord("a") + col)
            x = self._bx + col * self._cell + self._cell // 2 - 5
            canvas.put_text(file, x, self._by - 8, 0.6, _TEXT, 1)
            canvas.put_text(file, x, self._by + self._board_px + 20, 0.6, _TEXT, 1)
        for row in range(model.height):
            rank = str(model.height - row)
            y = self._by + row * self._cell + self._cell // 2 + 6
            canvas.put_text(rank, self._bx - 20, y, 0.6, _TEXT, 1)
            canvas.put_text(rank, self._bx + self._board_px + 10, y, 0.6, _TEXT, 1)

    def _draw_game_over(self, canvas):
        self._banner.draw_on(canvas, self._bx, self._by + self._board_px // 2 - 45)
        text = "GAME OVER"
        canvas.put_text(text, self._bx + self._board_px // 2 - 210,
                        self._by + self._board_px // 2 + 15, 2.0, _BANNER_TEXT, 4)

    def _centered(self, text):
        """Approximate x so `text` is roughly centered over the board (Img exposes
        no text-measuring, so this estimates the width from the character count)."""
        return self._bx + self._board_px // 2 - len(text) * _APPROX_CHAR_PX // 2
