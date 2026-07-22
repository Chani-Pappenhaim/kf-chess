"""Updating ELO when a game ends.

One more subscriber on the game's bus, beside the broadcaster. The engine
announces GameEnded with a winner; this looks up who was playing each colour,
moves both ratings by ELO, and writes them back - to the store, so they persist,
and to the registry, so the next state shows them.

The engine never learns what a rating is: winning a game and being rated for it
are two separate concerns, joined only here.
"""
from __future__ import annotations

from accounts.elo import updated
from game.events import GameEnded


def subscribe_ratings(bus, registry, store, config):
    """Wire ELO updates onto `bus`. Needs the registry to turn a winning colour
    into the two usernames, and the store to persist their new ratings."""
    def on_game_ended(event):
        winner = event.winner
        loser = _other_color(config.COLORS, winner)
        _apply(registry, store, config, winner, loser)

    bus.subscribe(GameEnded, on_game_ended)


def _apply(registry, store, config, winner, loser):
    winner_name = registry.name_of(winner)
    loser_name = registry.name_of(loser)
    # Both seats must be filled: a game with only one player seated has no
    # opponent to rate against, so nothing moves.
    if winner_name is None or loser_name is None:
        return
    new_winner, new_loser = updated(
        registry.ratings()[winner], registry.ratings()[loser], config.ELO_K_FACTOR
    )
    _record(registry, store, winner, winner_name, new_winner)
    _record(registry, store, loser, loser_name, new_loser)


def _record(registry, store, color, username, rating):
    store.set_rating(username, rating)     # persists across runs
    registry.set_rating(color, rating)     # shows in the next state


def _other_color(colors, color):
    return next(other for other in colors if other != color)
