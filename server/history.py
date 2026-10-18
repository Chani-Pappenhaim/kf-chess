"""Recording a finished game's result.

One more subscriber on the game's bus, beside the broadcaster and the ELO
update - the same GameEnded event, a different concern. Publishes to `queue`
rather than writing to the history store directly, for the same reason
`server/ratings.py` does: a game ending must never block on a database write,
and a write that fails should retry instead of losing the result. See
`server/results_worker.py` for where the write actually happens.

The engine never learns what history is; winning a game and being remembered
for it are two separate things, joined only here.
"""
from __future__ import annotations

import uuid

from game.events import GameEnded


def subscribe_history(bus, registry, queue, config):
    """Wire result recording onto `bus`. Needs the registry to turn a winning
    colour into the two usernames, and `queue` to hand the result to the
    durable results pipeline."""
    def on_game_ended(event):
        winner_color = event.winner
        loser_color = _other_color(config.COLORS, winner_color)
        winner = registry.name_of(winner_color)
        loser = registry.name_of(loser_color)
        # Both seats must be filled: a game with only one player seated has no
        # opponent to record a result against.
        if winner is None or loser is None:
            return
        queue.publish({
            "kind": "history",
            "winner": winner, "loser": loser,
            "reason": event.reason, "at_ms": event.at_ms,
            # Minted once, here, at publish time - not by the worker that
            # applies it. A message redelivered after a crash (at-least-once)
            # carries the SAME id, so history_store.record's UNIQUE(result_id)
            # recognises the replay as the game already recorded, not a new one.
            "result_id": str(uuid.uuid4()),
        })

    bus.subscribe(GameEnded, on_game_ended)


def _other_color(colors, color):
    return next(other for other in colors if other != color)
