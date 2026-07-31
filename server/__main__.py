"""KungFu Chess - the server. Run with `python -m server`.

The third entry point, beside main.py and play.py, and it builds the same graph
they do: the board from CSV, the rest from game.composition. What it adds is the
two directions of the wire - events out, commands in - and the clock, which from
here on runs on the server and nowhere else.
"""
from __future__ import annotations

import asyncio

from accounts.history_store import PostgresHistoryStore, SqliteHistoryStore
from accounts.postgres_store import PostgresAccountStore
from accounts.sqlite_store import SqliteAccountStore
from board.loaders import load_csv_board, load_snapshot_board
from config import settings
from events.bus import EventBus
from game.composition import build_engine, build_registry
from logs.activity_log import file_log
from server.active_rooms import InMemoryActiveRooms, RedisActiveRooms
from server.allocator import GameAllocator, parse_pool
from server.api import ApiGateway
from server.broadcast import subscribe_broadcast
from server.history import subscribe_history
from server.lobby import Lobby
from server.matchmaking import Matchmaker
from server.matchmaking_queue import InMemoryMatchmakingQueue, RedisMatchmakingQueue
from server.outbox import Outbox
from server.pubsub import RedisPubSub
from server.ratings import subscribe_ratings
from server.registry import PlayerRegistry
from server.room import Room
from server.room_snapshots import InMemoryRoomSnapshots, RedisRoomSnapshots
from server.service import GameService
from server.socket import WebSocketServer
from server.tokens import InMemoryTokenStore, RedisTokenStore


def load_board(config, snapshot=None):
    """A fresh board for a room - from the CSV starting position, or from a
    saved snapshot's piece positions when rehydrating a room whose
    game-server process died (see server/room_snapshots.py)."""
    registry = build_registry(config)
    if snapshot is not None:
        pieces = [(token, tuple(cell)) for token, cell in snapshot["pieces"]]
        board = load_snapshot_board(pieces, snapshot["width"], snapshot["height"], registry, config)
        return board, registry
    with open(config.BOARD_CSV, encoding="utf-8") as handle:
        return load_csv_board(handle.read().splitlines(), registry, config), registry


def build_room(room_id, config, store, history, room_snapshots=None, snapshot=None):
    """One room's whole graph: a fresh board and engine, a registry to seat its
    two players, and this room's own broadcaster, rating, and history
    subscribers on its own bus - so nothing it publishes reaches any other room.

    `snapshot`, when given, rebuilds the board and seats from a saved position
    instead of a fresh game - `Lobby.room()`'s rehydration path, not normal
    creation. `room_snapshots` is where this room mirrors its own position to
    as it plays, regardless of whether it started fresh or rehydrated.
    """
    board, rule_registry = load_board(config, snapshot)
    bus = EventBus()
    engine = build_engine(board, rule_registry, config, bus)
    players = PlayerRegistry(config.COLORS)
    if snapshot is not None:
        players.restore(snapshot["players"])
    room = Room(room_id, engine, players, board.height, config, room_snapshots)
    subscribe_broadcast(bus, room.broadcast)
    subscribe_ratings(bus, players, store, config)
    subscribe_history(bus, players, history, config)
    return room


def build_service(config=settings, store=None, tokens=None, queue=None, bus=None,
                   active_rooms=None, history=None, room_snapshots=None):
    """The server, wired to host many games. Returns the outbox (to drain) and
    the service the socket drives.

    `store`, `tokens`, `queue`, `bus`, `active_rooms`, `history`, and
    `room_snapshots` are injectable so a test can pass fakes instead of real
    infrastructure; the server proper builds them from config and shares them
    with the API Gateway (see run()). Room placement is computed from
    GAME_SERVERS, the same pool the WebSocket Gateway routes by - a single
    entry (the default) always resolves to this one server.
    """
    accounts = store or _default_account_store(config)
    game_history = history or _default_history_store(config)
    session_tokens = tokens or InMemoryTokenStore()
    matchmaking_queue = queue or InMemoryMatchmakingQueue(config)
    snapshots = room_snapshots or InMemoryRoomSnapshots()
    allocator = GameAllocator(parse_pool(config.GAME_SERVERS).keys())
    outbox = Outbox()
    lobby = Lobby(
        lambda room_id: build_room(room_id, config, accounts, game_history, snapshots),
        config.SERVER_ID,
        active_rooms or InMemoryActiveRooms(),
        snapshots=snapshots,
        rehydrate=lambda room_id, snap: build_room(room_id, config, accounts, game_history, snapshots, snap),
    )
    matchmaker = Matchmaker(lobby, matchmaking_queue, config, allocator, config.SERVER_ID, bus)
    return outbox, GameService(lobby, matchmaker, session_tokens, config)


def _default_account_store(config):  # pragma: no cover - connects to a real database
    if config.DATABASE_URL:
        return PostgresAccountStore(config.DATABASE_URL, config.STARTING_RATING)
    return SqliteAccountStore(config.ACCOUNTS_DB, config.STARTING_RATING)


def _default_history_store(config):  # pragma: no cover - connects to a real database
    if config.DATABASE_URL:
        return PostgresHistoryStore(config.DATABASE_URL)
    return SqliteHistoryStore(config.HISTORY_DB)


def run(config=settings):  # pragma: no cover - runs until interrupted
    accounts = _default_account_store(config)
    history = _default_history_store(config)
    # Distributed: tokens, the matchmaking queue, the redirect bus, and room
    # snapshots move to Redis, shared with the other Game Servers and the
    # Gateway routing them.
    if config.DISTRIBUTED:
        tokens = RedisTokenStore(config.REDIS_URL)
        queue = RedisMatchmakingQueue(config.REDIS_URL, config)
        bus = RedisPubSub(config.REDIS_URL)
        active_rooms = RedisActiveRooms(config.REDIS_URL)
        room_snapshots = RedisRoomSnapshots(config.REDIS_URL)
    else:
        tokens = InMemoryTokenStore()
        queue = InMemoryMatchmakingQueue(config)
        bus = None
        active_rooms = None
        room_snapshots = None
    outbox, service = build_service(
        config, store=accounts, tokens=tokens, queue=queue, bus=bus,
        active_rooms=active_rooms, history=history, room_snapshots=room_snapshots,
    )
    ApiGateway(config, accounts, tokens, service, history).start()
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
