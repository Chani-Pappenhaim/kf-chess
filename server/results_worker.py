"""Drains `server/results_queue.py` and makes the writes `server/ratings.py`/
`server/history.py` used to make in-line, now durable and off the game
server's own thread.

Run with `python -m server.results_worker` - a service of its own, so a slow
or briefly-unreachable database only backs up this queue, never a room's
clock. At-least-once: a batch's offsets are only committed once every write
in it has succeeded (`queue.commit()` below), so a crash mid-batch replays
from the last commit rather than losing anything. That replay is safe to
reapply: `set_rating` is a plain overwrite, and `history.record` carries the
`result_id` minted once at publish time (`server/history.py`), so a redelivered
message is recognised as the same result and not inserted twice.
"""
from __future__ import annotations

import time

from accounts.factory import account_store_for, history_store_for
from config import settings
from server.results_queue import InMemoryResultsQueue, KafkaResultsQueue

_POLL_IDLE_SECONDS = 0.5


def process_batch(queue, accounts, history):
    """Apply every result currently pending, then commit - so a redelivery
    after a mid-batch crash starts from the last fully-applied batch, not
    from wherever it happened to stop. Returns how many were applied, so a
    caller (or a test) can tell an idle poll from real work."""
    payloads = queue.consume()
    for payload in payloads:
        _apply(payload, accounts, history)
    if payloads:
        queue.commit()
    return len(payloads)


def _apply(payload, accounts, history):
    kind = payload["kind"]
    if kind == "rating":
        accounts.set_rating(payload["username"], payload["rating"])
    elif kind == "history":
        history.record(
            payload["winner"], payload["loser"], payload["reason"], payload["at_ms"],
            result_id=payload.get("result_id"),
        )


def run(config=settings):  # pragma: no cover - runs until interrupted
    # The same factory server/__main__.py uses: a sharded account store when
    # KF_DATABASE_URLS is set, so a rating this worker writes always lands on
    # the same shard the Game Server reads it from.
    accounts = account_store_for(config)
    history = history_store_for(config)
    queue = KafkaResultsQueue(config.KAFKA_URL) if config.DISTRIBUTED else InMemoryResultsQueue()
    print(f"KungFu Chess results worker draining {config.KAFKA_URL if config.DISTRIBUTED else '(in-memory, single-process only)'}")
    try:
        while True:
            applied = process_batch(queue, accounts, history)
            if applied == 0:
                time.sleep(_POLL_IDLE_SECONDS)
    except KeyboardInterrupt:
        print(config.SERVER_STOPPED_MESSAGE)


if __name__ == "__main__":  # pragma: no cover
    run()
