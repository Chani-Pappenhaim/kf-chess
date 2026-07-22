"""KungFu Chess - the server. Run with `python -m server`.

The third entry point, beside main.py and play.py, and it builds the same graph
they do: the board from CSV, the rest from game.composition. What it adds is the
two directions of the wire - events out, commands in - and the clock, which from
here on runs on the server and nowhere else.
"""
from __future__ import annotations

import asyncio

from accounts.sqlite_store import SqliteAccountStore
from board.loaders import load_csv_board
from config import settings
from events.bus import EventBus
from game.composition import build_engine, build_registry
from server.broadcast import subscribe_broadcast
from server.outbox import Outbox
from server.ratings import subscribe_ratings
from server.registry import PlayerRegistry
from server.service import GameService
from server.socket import WebSocketServer


def load_board(config):
    """The board this entry point hosts. Loading it is the only thing it knows
    that the other entry points do not."""
    registry = build_registry(config)
    with open(config.BOARD_CSV, encoding="utf-8") as handle:
        return load_csv_board(handle.read().splitlines(), registry, config), registry


def build_service(config=settings, store=None):
    """The game, wired to announce itself. Returns the engine (to start), the
    outbox (to drain), and the service the socket drives.

    `store` is injectable so a test can pass a fake account store instead of a
    real SQLite file; the server proper opens the database from config.
    """
    board, rule_registry = load_board(config)
    bus = EventBus()
    engine = build_engine(board, rule_registry, config, bus)
    outbox = Outbox()
    players = PlayerRegistry(config.COLORS)
    accounts = store or SqliteAccountStore(config.ACCOUNTS_DB, config.STARTING_RATING)
    subscribe_broadcast(bus, outbox.to_all)
    subscribe_ratings(bus, players, accounts, config)
    return engine, outbox, GameService(engine, board.height, outbox, players, accounts)


def run(config=settings):  # pragma: no cover - runs until interrupted
    engine, outbox, service = build_service(config)
    engine.start()
    try:
        print(f"KungFu Chess server listening on {config.SERVER_URL}")
        asyncio.run(WebSocketServer(config, outbox, service).run())
    except OSError as error:
        # Almost always a server already running on that port. A stack trace
        # says nothing a person can act on; the address and the reason do.
        print(f"cannot listen on {config.SERVER_URL}: {error.strerror}")
    except KeyboardInterrupt:
        print("server stopped")


if __name__ == "__main__":  # pragma: no cover
    run()
