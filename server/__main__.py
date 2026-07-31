"""KungFu Chess - the server. Run with `python -m server`.

The third entry point, beside main.py and play.py, and it builds the same graph
they do: the board from CSV, the rest from game.composition. What it adds is the
two directions of the wire - events out, commands in - and the clock, which from
here on runs on the server and nowhere else.
"""
from __future__ import annotations

import asyncio

from accounts.postgres_store import PostgresAccountStore
from accounts.sqlite_store import SqliteAccountStore
from board.loaders import load_csv_board
from config import settings
from events.bus import EventBus
from game.composition import build_engine, build_registry
from logs.activity_log import file_log
from server.active_rooms import InMemoryActiveRooms, RedisActiveRooms
from server.allocator import GameAllocator, parse_pool
from server.api import ApiGateway
from server.broadcast import subscribe_broadcast
from server.lobby import Lobby
from server.matchmaking import Matchmaker
from server.matchmaking_queue import InMemoryMatchmakingQueue, RedisMatchmakingQueue
from server.outbox import Outbox
from server.pubsub import RedisPubSub
from server.ratings import subscribe_ratings
from server.registry import PlayerRegistry
from server.room import Room
from server.service import GameService
from server.socket import WebSocketServer
from server.tokens import InMemoryTokenStore, RedisTokenStore


def load_board(config):
    """A fresh board for a room. Loaded per room, not once, so two games never
    share the same pieces; loading it is the only thing this entry point knows
    that the others do not."""
    registry = build_registry(config)
    with open(config.BOARD_CSV, encoding="utf-8") as handle:
        return load_csv_board(handle.read().splitlines(), registry, config), registry


def build_room(room_id, config, store):
    """One room's whole graph: a fresh board and engine, a registry to seat its
    two players, and this room's own broadcaster and rating subscriber on its own
    bus - so nothing it publishes reaches any other room."""
    board, rule_registry = load_board(config)
    bus = EventBus()
    engine = build_engine(board, rule_registry, config, bus)
    players = PlayerRegistry(config.COLORS)
    room = Room(room_id, engine, players, board.height, config)
    subscribe_broadcast(bus, room.broadcast)
    subscribe_ratings(bus, players, store, config)
    return room


def build_service(config=settings, store=None, tokens=None, queue=None, bus=None, active_rooms=None):
    """The server, wired to host many games. Returns the outbox (to drain) and
    the service the socket drives.

    `store`, `tokens`, `queue`, `bus`, and `active_rooms` are injectable so a
    test can pass fakes instead of real infrastructure; the server proper
    builds them from config and shares them with the API Gateway (see run()).
    Room placement is computed from GAME_SERVERS, the same pool the WebSocket
    Gateway routes by - a single entry (the default) always resolves to this
    one server.
    """
    accounts = store or _default_account_store(config)
    session_tokens = tokens or InMemoryTokenStore()
    matchmaking_queue = queue or InMemoryMatchmakingQueue(config)
    allocator = GameAllocator(parse_pool(config.GAME_SERVERS).keys())
    outbox = Outbox()
    lobby = Lobby(
        lambda room_id: build_room(room_id, config, accounts), config.SERVER_ID,
        active_rooms or InMemoryActiveRooms(),
    )
    matchmaker = Matchmaker(lobby, matchmaking_queue, config, allocator, config.SERVER_ID, bus)
    return outbox, GameService(lobby, matchmaker, session_tokens, config)


def _default_account_store(config):  # pragma: no cover - connects to a real database
    if config.DATABASE_URL:
        return PostgresAccountStore(config.DATABASE_URL, config.STARTING_RATING)
    return SqliteAccountStore(config.ACCOUNTS_DB, config.STARTING_RATING)


def run(config=settings):  # pragma: no cover - runs until interrupted
    accounts = _default_account_store(config)
    # Distributed: tokens, the matchmaking queue, and the redirect bus move to
    # Redis, shared with the other Game Servers and the Gateway routing them.
    if config.DISTRIBUTED:
        tokens = RedisTokenStore(config.REDIS_URL)
        queue = RedisMatchmakingQueue(config.REDIS_URL, config)
        bus = RedisPubSub(config.REDIS_URL)
        active_rooms = RedisActiveRooms(config.REDIS_URL)
    else:
        tokens = InMemoryTokenStore()
        queue = InMemoryMatchmakingQueue(config)
        bus = None
        active_rooms = None
    outbox, service = build_service(
        config, store=accounts, tokens=tokens, queue=queue, bus=bus, active_rooms=active_rooms,
    )
    ApiGateway(config, accounts, tokens, service).start()
    log = file_log(config.SERVER_LOG_PATH, "kfchess.server")
    try:
        print(f"KungFu Chess server listening on {config.SERVER_URL}")
        asyncio.run(WebSocketServer(config, outbox, service, log).run())
    except OSError as error:
        # Almost always a server already running on that port. A stack trace
        # says nothing a person can act on; the address and the reason do.
        print(f"cannot listen on {config.SERVER_URL}: {error.strerror}")
    except KeyboardInterrupt:
        print(config.SERVER_STOPPED_MESSAGE)


if __name__ == "__main__":  # pragma: no cover
    run()
