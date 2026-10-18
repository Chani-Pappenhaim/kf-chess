"""The home screen - Play, Room, Computer - and the colour screen after it.

Shown after login, before any game. Play asks the server for a quick match; Room
opens the native dialog to create or join one by id; Computer leads to a second
screen of the same kind, White / Black / Random, for a game against the
computer. Each screen only draws its buttons and says which one a click landed
on - what those choices mean is the caller's business, so the drawing and
hit-testing here stay free of the network.

The button geometry and the click test are pure and unit-tested; run_menu is
the thin cv2 loop around them.
"""
from __future__ import annotations

from graphics.assets import solid

_BACKGROUND = (238, 238, 238, 255)
_TEXT = (35, 35, 35, 255)
_APPROX_CHAR_PX = 11  # rough per-character width, for centring a label

RANDOM_COLOR = "random"   # the colour screen's third choice: let the server pick


class ButtonMenu:
    """A column of labelled buttons, centred in the window. `buttons` is a
    sequence of (choice, label); a click on a button answers its choice."""

    def __init__(self, config, buttons):
        self._config = config
        bw, bh, gap = (
            config.HOME_BUTTON_WIDTH, config.HOME_BUTTON_HEIGHT, config.HOME_BUTTON_GAP
        )
        left = config.WINDOW_WIDTH // 2 - bw // 2
        top = config.WINDOW_HEIGHT // 2 - (len(buttons) * bh + (len(buttons) - 1) * gap) // 2
        self._buttons = tuple(
            (choice, label, (left, top + i * (bh + gap), bw, bh))
            for i, (choice, label) in enumerate(buttons)
        )

    def button_at(self, x, y):
        """Which button a click hit - its choice - or None for a miss."""
        for choice, _label, rect in self._buttons:
            if self._within(rect, x, y):
                return choice
        return None

    def canvas(self):
        """The menu as a fresh canvas Img."""
        canvas = solid(self._config.WINDOW_WIDTH, self._config.WINDOW_HEIGHT, _BACKGROUND)
        for _choice, label, rect in self._buttons:
            self._draw_button(canvas, rect, label)
        return canvas

    def _within(self, rect, x, y):
        rx, ry, rw, rh = rect
        return rx <= x < rx + rw and ry <= y < ry + rh

    def _draw_button(self, canvas, rect, label):
        rx, ry, rw, rh = rect
        solid(rw, rh, self._config.HOME_BUTTON_COLOR).draw_on(canvas, rx, ry)
        tx = rx + rw // 2 - len(label) * _APPROX_CHAR_PX // 2
        canvas.put_text(label, tx, ry + rh // 2 + 8, 0.9, _TEXT, 2)


def home_menu(config):
    """The screen after login: "play", "room", or "computer"."""
    return ButtonMenu(config, (
        ("play", config.PLAY_BUTTON_TEXT),
        ("room", config.ROOM_BUTTON_TEXT),
        ("computer", config.COMPUTER_BUTTON_TEXT),
    ))


def color_menu(config):
    """The colour to play the computer with: "w", "b", or RANDOM_COLOR."""
    return ButtonMenu(config, (
        ("w", config.WHITE_BUTTON_TEXT),
        ("b", config.BLACK_BUTTON_TEXT),
        (RANDOM_COLOR, config.RANDOM_COLOR_BUTTON_TEXT),
    ))


def requested_color(choice):
    """What PlayComputer carries for a colour-screen choice: the colour itself,
    or "" for Random - the server picks then, so the client holds no rng."""
    return "" if choice == RANDOM_COLOR else choice


def run_menu(window, menu):  # pragma: no cover - real-time GUI loop
    """Draw `menu` until a button is clicked (returns its choice) or the window
    is closed (returns None)."""
    while True:
        window.show(menu.canvas())
        for event in window.poll_events():
            if event[0] == "quit":
                return None
            if event[0] == "left":
                choice = menu.button_at(event[1], event[2])
                if choice is not None:
                    return choice
