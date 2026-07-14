"""Hud - score, clock and game-over overlays, drawn through Img.

A view component like GraphicsRenderer: it takes the read model and draws onto
the canvas, touching neither the engine nor cv2. Material counts are derived
from the model's pieces, the clock from its elapsed time, and a banner is laid
over the board when the game is over. Text goes through Img.put_text and the
banner through Img.draw_on of a translucent overlay.
"""
from __future__ import annotations

from graphics.assets import solid

_TEXT_COLOR = (255, 255, 255, 255)     # white (BGRA)
_BANNER_BG = (0, 0, 0, 180)            # translucent black
_BANNER_TEXT = (0, 0, 255, 255)        # red


class Hud:
    def __init__(self, config):
        self._board_px = config.BOARD_PX
        self._strip_baseline = config.BOARD_PX + 45
        self._banner = solid(config.BOARD_PX, 90, _BANNER_BG)

    def draw(self, canvas, model):
        white = sum(1 for piece in model.pieces if piece.token[0] == "w")
        black = sum(1 for piece in model.pieces if piece.token[0] == "b")
        canvas.put_text(f"White: {white}", 15, self._strip_baseline, 1.0, _TEXT_COLOR, 2)
        canvas.put_text(
            f"Black: {black}", self._board_px // 2 - 40, self._strip_baseline, 1.0, _TEXT_COLOR, 2
        )
        canvas.put_text(
            f"{model.clock // 1000}s", self._board_px - 95, self._strip_baseline, 1.0, _TEXT_COLOR, 2
        )
        if model.game_over:
            self._draw_game_over(canvas)

    def _draw_game_over(self, canvas):
        self._banner.draw_on(canvas, 0, self._board_px // 2 - 45)
        canvas.put_text(
            "GAME OVER", self._board_px // 2 - 210, self._board_px // 2 + 15, 2.0, _BANNER_TEXT, 4
        )
