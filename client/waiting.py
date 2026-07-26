"""The screen shown while there is no game to draw yet.

A client opens its window before the server has told it anything. Rather than
invent an empty board to stand in - a dummy the rest of the code would have to
tolerate forever - it draws this until the first state arrives.
"""
from __future__ import annotations

from graphics.assets import solid

_BACKGROUND = (238, 238, 238, 255)
_TEXT = (35, 35, 35, 255)
_APPROX_CHAR_PX = 12  # rough per-character width at the scale below, for centring


def waiting_canvas(config, message):
    """A plain window with `message` across the middle of it."""
    canvas = solid(config.WINDOW_WIDTH, config.WINDOW_HEIGHT, _BACKGROUND)
    x = config.WINDOW_WIDTH // 2 - len(message) * _APPROX_CHAR_PX // 2
    canvas.put_text(message, x, config.WINDOW_HEIGHT // 2, 1.0, _TEXT, 2)
    return canvas


def wait_for_state(window, inbox, identity, config):
    """Hold the window on the waiting screen until a state arrives.

    Returns the state, or None if the player closed the window, the connection
    dropped, or the server turned them away - the things that can end the wait
    without a game. The caller tells them apart by asking `identity`.
    """
    while True:
        if identity.rejected() or identity.lost():
            return None
        model = inbox.model()
        if model is not None:
            return model
        window.show(waiting_canvas(config, config.CONNECTING_TEXT))
        for event in window.poll_events():
            if event[0] == "quit":
                return None
