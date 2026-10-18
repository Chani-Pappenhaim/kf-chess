"""Updating ELO when a game ends.

One more subscriber on the game's bus, beside the broadcaster. The engine
announces GameEnded with a winner; this looks up who was playing each colour,
moves both ratings by ELO, and applies them - to the registry immediately, so
the next state shows them, and to `queue` for `server/results_worker.py` to
persist durably.

The ELO math itself still happens here, synchronously, off the registry's own
in-memory ratings - it is pure and cheap, and the registry is the correct
source of "current rating" for the duration of a live game (seeded from the
store at seat time). Only the *write* to the account store - the part that
can block or fail - is deferred to the queue, so a room's clock is never
paused waiting on a database, and a result that fails to persist retries
instead of vanishing.

The engine never learns what a rating is: winning a game and being rated for
it are two separate concerns, joined only here.
"""
from __future__ import annotations

from accounts.elo import updated
from game.events import GameEnded


def subscribe_ratings(bus, registry, queue, config):
    """Wire ELO updates onto `bus`. Needs the registry to turn a winning colour
    into the two usernames and to hold their live ratings, and `queue` to hand
    the final numbers to the durable results pipeline."""
    def on_game_ended(event):
        winner = event.winner
        loser = _other_color(config.COLORS, winner)
        _apply(registry, queue, config, winner, loser)

    bus.subscribe(GameEnded, on_game_ended)


def _apply(registry, queue, config, winner, loser):
    winner_name = registry.name_of(winner)
    loser_name = registry.name_of(loser)
    # Both seats must be filled: a game with only one player seated has no
    # opponent to rate against, so nothing moves.
    if winner_name is None or loser_name is None:
        return
    # A game against the computer is practice: it has no rating to win from
    # or lose to, so no one's rating moves.
    if registry.is_computer(winner) or registry.is_computer(loser):
        return
    new_winner, new_loser = updated(
        registry.ratings()[winner], registry.ratings()[loser], config.ELO_K_FACTOR
    )
    _record(registry, queue, winner, winner_name, new_winner)
    _record(registry, queue, loser, loser_name, new_loser)


def _record(registry, queue, color, username, rating):
    queue.publish({"kind": "rating", "username": username, "rating": rating})
    registry.set_rating(color, rating)     # shows in the next state, right now


def _other_color(colors, color):
    return next(other for other in colors if other != color)
