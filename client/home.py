"""The home screen: two buttons, Play and Room.

Shown after login, before any game. Play asks the server for a quick match; Room
opens the native dialog to create or join one by id. The screen only draws the
buttons and says which one a click landed on - what those choices mean is the
caller's business, so the drawing and hit-testing here stay free of the network.

The button geometry and the click test are pure and unit-tested; run_home is the
thin cv2 loop around them.
"""
from __future__ import annotations

from graphics.assets import solid

_BACKGROUND = (238, 238, 238, 255)
_TEXT = (35, 35, 35, 255)
_APPROX_CHAR_PX = 11  # rough per-character width, for centring a label


class HomeScreen:
    def __init__(self, config):
        self._config = config
        width, height = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        bw, bh, gap = (
            config.HOME_BUTTON_WIDTH, config.HOME_BUTTON_HEIGHT, config.HOME_BUTTON_GAP
        )
        left = width // 2 - bw // 2
        top = height // 2 - (2 * bh + gap) // 2
        self._play = (left, top, bw, bh)
        self._room = (left, top + bh + gap, bw, bh)

    def button_at(self, x, y):
        """Which button a click hit: "play", "room", or None for a miss."""
        if self._within(self._play, x, y):
            return "play"
        if self._within(self._room, x, y):
            return "room"
        return None

    def canvas(self):
        """The home screen as a fresh canvas Img."""
        canvas = solid(self._config.WINDOW_WIDTH, self._config.WINDOW_HEIGHT, _BACKGROUND)
        self._draw_button(canvas, self._play, self._config.PLAY_BUTTON_TEXT)
        self._draw_button(canvas, self._room, self._config.ROOM_BUTTON_TEXT)
        return canvas

    def _within(self, rect, x, y):
        rx, ry, rw, rh = rect
        return rx <= x < rx + rw and ry <= y < ry + rh

    def _draw_button(self, canvas, rect, label):
        rx, ry, rw, rh = rect
        solid(rw, rh, self._config.HOME_BUTTON_COLOR).draw_on(canvas, rx, ry)
        tx = rx + rw // 2 - len(label) * _APPROX_CHAR_PX // 2
        canvas.put_text(label, tx, ry + rh // 2 + 8, 0.9, _TEXT, 2)


def run_home(window, home):  # pragma: no cover - real-time GUI loop
    """Draw the home screen until a button is clicked (returns "play"/"room") or
    the window is closed (returns None)."""
    while True:
        window.show(home.canvas())
        for event in window.poll_events():
            if event[0] == "quit":
                return None
            if event[0] == "left":
                choice = home.button_at(event[1], event[2])
                if choice is not None:
                    return choice
