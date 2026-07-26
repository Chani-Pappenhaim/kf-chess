"""The banner overlaid on the board when the game opens and when it ends.

A subscriber that keeps only what to show and until when. The Hud asks it each
frame, so the drawing stays in the Hud and the timing stays here.

The two facts - the text and how long it lasts - are held as one tuple, and
replaced in a single assignment. A subscriber fires on the network thread while
the Hud reads on the frame thread, so text and expiry must never be seen from
two different banners: swapping the pair in one step is what guarantees that,
without a lock.
"""
from __future__ import annotations

from game.events import GameStarted, GameEnded

_FOREVER = float("inf")
_NOTHING = (None, 0)  # no text, and an expiry no clock reading is below


class BannerAnimation:
    def __init__(self, config):
        self._config = config
        self._showing = _NOTHING  # (text, expiry_ms)

    def announce_start(self, event):
        self._show(
            self._config.START_BANNER_TEXT, event.at_ms + self._config.START_BANNER_MS
        )

    def announce_end(self, event):
        winner = self._config.COLOR_NAMES[event.winner].upper()
        # A forfeit (a player who left) says so, so the winner is not left to
        # think they were beaten on the board.
        template = (
            self._config.FORFEIT_BANNER_TEXT
            if event.reason == self._config.GAME_END_FORFEIT
            else self._config.END_BANNER_TEXT
        )
        self._show(template.format(winner=winner), _FOREVER)

    def text_at(self, clock):
        """What to draw now, or None when nothing is showing. Before the first
        event the expiry is 0, so no clock reading can bring a banner up."""
        text, until = self._showing
        return text if clock < until else None

    def _show(self, text, until):
        self._showing = (text, until)


def subscribe_banner(bus, config):
    """Wire a banner onto `bus` and hand it back for the Hud to read."""
    banner = BannerAnimation(config)
    bus.subscribe(GameStarted, banner.announce_start)
    bus.subscribe(GameEnded, banner.announce_end)
    return banner
