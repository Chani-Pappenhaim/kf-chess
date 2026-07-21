"""The banner overlaid on the board when the game opens and when it ends.

A subscriber that keeps only what to show and until when. The Hud asks it each
frame, so the drawing stays in the Hud and the timing stays here.
"""
from __future__ import annotations

from game.events import GameStarted, GameEnded

_FOREVER = float("inf")


class BannerAnimation:
    def __init__(self, config):
        self._config = config
        self._text = None
        self._until = 0

    def announce_start(self, event):
        self._show(
            self._config.START_BANNER_TEXT, event.at_ms + self._config.START_BANNER_MS
        )

    def announce_end(self, event):
        winner = self._config.COLOR_NAMES[event.winner].upper()
        self._show(self._config.END_BANNER_TEXT.format(winner=winner), _FOREVER)

    def text_at(self, clock):
        """What to draw now, or None when nothing is showing. Before the first
        event `_until` is 0, so no clock reading can bring a banner up."""
        return self._text if clock < self._until else None

    def _show(self, text, until):
        self._text = text
        self._until = until


def subscribe_banner(bus, config):
    """Wire a banner onto `bus` and hand it back for the Hud to read."""
    banner = BannerAnimation(config)
    bus.subscribe(GameStarted, banner.announce_start)
    bus.subscribe(GameEnded, banner.announce_end)
    return banner
