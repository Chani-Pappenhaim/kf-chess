"""KungFu Chess - the server. Run with `python -m server`.

The third entry point, beside main.py and play.py, and it builds the same graph
they do: the board from CSV, the rest from game.composition. What it adds is the
two directions of the wire - events out, commands in - and the clock, which from
here on runs on the server and nowhere else.
"""
from __future__ import annotations

import asyncio

from board.loaders import load_csv_board
from config import settings
from events.bus import EventBus
from game.composition import build_engine, build_registry
from server.broadcast import subscribe_broadcast
from server.outbox import Outbox
from server.service import GameService
from server.socket import WebSocketServer


def load_board(config):
    """The board this entry point hosts. Loading it is the only thing it knows
    that the other entry points do not."""
    registry = build_registry(config)
    with open(config.BOARD_CSV, encoding="utf-8") as handle:
        return load_csv_board(handle.read().splitlines(), registry, config), registry


def build_service(config=settings):
    """The game, wired to announce itself. Returns the engine (to start), the
    outbox (to drain), and the service the socket drives."""
    board, registry = load_board(config)
    bus = EventBus()
    engine = build_engine(board, registry, config, bus)
    outbox = Outbox()
    subscribe_broadcast(bus, outbox.to_all)
    return engine, outbox, GameService(engine, board.height, outbox)


def run(config=settings):  # pragma: no cover - runs until interrupted
    engine, outbox, service = build_service(config)
    engine.start()
    print(f"KungFu Chess server listening on {config.SERVER_URL}")
    asyncio.run(WebSocketServer(config, outbox, service).run())


if __name__ == "__main__":  # pragma: no cover
    run()
