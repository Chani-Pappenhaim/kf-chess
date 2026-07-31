"""Recording a finished game's result.

One more subscriber on the game's bus, beside the broadcaster and the ELO
update - the same GameEnded event, a different concern. The engine never
learns what history is; winning a game and being remembered for it are two
separate things, joined only here.
"""
from __future__ import annotations

from game.events import GameEnded


def subscribe_history(bus, registry, store, config):
    """Wire result recording onto `bus`. Needs the registry to turn a winning
    colour into the two usernames, and the store to persist the result."""
    def on_game_ended(event):
        winner_color = event.winner
        loser_color = _other_color(config.COLORS, winner_color)
        winner = registry.name_of(winner_color)
        loser = registry.name_of(loser_color)
        # Both seats must be filled: a game with only one player seated has no
        # opponent to record a result against.
        if winner is None or loser is None:
            return
        store.record(winner, loser, event.reason, event.at_ms)

    bus.subscribe(GameEnded, on_game_ended)


def _other_color(colors, color):
    return next(other for other in colors if other != color)
