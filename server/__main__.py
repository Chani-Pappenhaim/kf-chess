"""KungFu Chess - the server. Run with `python -m server`.

The third entry point, beside main.py and play.py, and it builds the same graph
they do: the board from CSV, the rest from game.composition. What it adds is the
two directions of the wire - events out, commands in - and the clock, which from
here on runs on the server and nowhere else.
"""
from __future__ import annotations

import asyncio

from accounts.factory import account_store_for, history_store_for
from board.loaders import load_csv_board, load_snapshot_board
from bot.factory import build_computer_players
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
from server.results_queue import InMemoryResultsQueue, KafkaResultsQueue
from server.results_worker import process_batch as apply_pending_results
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


def build_room(room_id, config, results_queue, room_snapshots=None, snapshot=None, computers=None):
    """One room's whole graph: a fresh board and engine, a registry to seat its
    two players, and this room's own broadcaster, rating, and history
    subscribers on its own bus - so nothing it publishes reaches any other room.

    `snapshot`, when given, rebuilds the board and seats from a saved position
    instead of a fresh game - `Lobby.room()`'s rehydration path, not normal
    creation. `room_snapshots` is where this room mirrors its own position to
    as it plays, regardless of whether it started fresh or rehydrated.
    `computers` (bot/factory.py's ComputerPlayers) makes the computer player
    for a room that seats one; without it, the room seats only people.

    Ratings and history no longer take a store directly: both publish onto
    `results_queue` and `server/results_worker.py` durably applies the writes
    off this process entirely - a room never blocks on a database.
    """
    board, rule_registry = load_board(config, snapshot)
    bus = EventBus()
    engine = build_engine(board, rule_registry, config, bus)
    players = PlayerRegistry(config.COLORS)
    if snapshot is not None:
        players.restore(snapshot["players"])
    computer_factory = (lambda color: computers.player(engine, color)) if computers else None
    room = Room(room_id, engine, players, board.height, config, room_snapshots, computer_factory)
    subscribe_broadcast(bus, room.broadcast)
    subscribe_ratings(bus, players, results_queue, config)
    subscribe_history(bus, players, results_queue, config)
    return room


def build_service(config=settings, store=None, tokens=None, queue=None, bus=None,
                   active_rooms=None, results_queue=None, room_snapshots=None, computers=None):
    """The server, wired to host many games. Returns the outbox (to drain) and
    the service the socket drives.

    `store`, `tokens`, `queue`, `bus`, `active_rooms`, `results_queue`, and
    `room_snapshots` (and `computers`, the computer opponent) are injectable so a test can pass fakes instead of real
    infrastructure; the server proper builds them from config and shares
    `store` with the API Gateway (see run()) - `results_queue` is shared with
    `server/results_worker.py` instead, a separate process, not this one.
    Room placement is computed from GAME_SERVERS, the same pool the WebSocket
    Gateway routes by - a single entry (the default) always resolves to this
    one server.
    """
    session_tokens = tokens or InMemoryTokenStore()
    matchmaking_queue = queue or InMemoryMatchmakingQueue(config)
    snapshots = room_snapshots or InMemoryRoomSnapshots()
    results = results_queue or InMemoryResultsQueue()
    bots = computers or build_computer_players(config)
    allocator = GameAllocator(parse_pool(config.GAME_SERVERS).keys())
    outbox = Outbox()
    lobby = Lobby(
        lambda room_id: build_room(room_id, config, results, snapshots, computers=bots),
        config.SERVER_ID,
        active_rooms or InMemoryActiveRooms(),
        snapshots=snapshots,
        rehydrate=lambda room_id, snap: build_room(room_id, config, results, snapshots, snap, bots),
    )
    matchmaker = Matchmaker(lobby, matchmaking_queue, config, allocator, config.SERVER_ID, bus, config.REGION)
    return outbox, GameService(lobby, matchmaker, session_tokens, config)


def run(config=settings):  # pragma: no cover - runs until interrupted
    accounts = account_store_for(config)
    # Distributed: tokens, the matchmaking queue, the redirect bus, room
    # snapshots, and finished-game results move to Redis/Kafka, shared with
    # the other Game Servers, the Gateway routing them, and (for results) the
    # separate `python -m server.results_worker` process.
    if config.DISTRIBUTED:
        tokens = RedisTokenStore(config.REDIS_URL)
        queue = RedisMatchmakingQueue(config.REDIS_URL, config)
        bus = RedisPubSub(config.REDIS_URL)
        active_rooms = RedisActiveRooms(config.REDIS_URL)
        room_snapshots = RedisRoomSnapshots(config.REDIS_URL)
        results_queue = KafkaResultsQueue(config.KAFKA_URL)
    else:
        tokens = InMemoryTokenStore()
        queue = InMemoryMatchmakingQueue(config)
        bus = None
        active_rooms = None
        room_snapshots = None
        results_queue = InMemoryResultsQueue()
    outbox, service = build_service(
        config, store=accounts, tokens=tokens, queue=queue, bus=bus,
        active_rooms=active_rooms, results_queue=results_queue, room_snapshots=room_snapshots,
    )
    history = history_store_for(config)
    ApiGateway(config, accounts, tokens, service, history).start()
    log = file_log(config.SERVER_LOG_PATH, "kfchess.server")
    try:
        print(f"KungFu Chess server listening on {config.SERVER_URL}")
        asyncio.run(_serve(config, outbox, service, log, results_queue, accounts, history))
    except OSError as error:
        # Almost always a server already running on that port. A stack trace
        # says nothing a person can act on; the address and the reason do.
        print(f"cannot listen on {config.SERVER_URL}: {error.strerror}")
    except KeyboardInterrupt:
        print(config.SERVER_STOPPED_MESSAGE)


async def _serve(config, outbox, service, log, results_queue, accounts, history):  # pragma: no cover
    """The socket loop, plus - only when not distributed - the results
    pipeline drained right here instead of by a separate
    `python -m server.results_worker` process. `InMemoryResultsQueue` cannot
    be shared across processes, so a bare `python -m server` needs this to
    still persist ratings/history the way it always could; a real deployment
    (`KF_DISTRIBUTED`) uses Kafka and the standalone worker instead, and this
    task is skipped entirely."""
    tasks = [WebSocketServer(config, outbox, service, log).run()]
    if not config.DISTRIBUTED:
        tasks.append(_drain_results_locally(results_queue, accounts, history))
    await asyncio.gather(*tasks)


async def _drain_results_locally(queue, accounts, history):  # pragma: no cover
    while True:
        # Off the event loop even here: the write itself must never block the
        # tick/socket loop it shares a process with, the same reasoning as
        # the login worker pool in server/api.py.
        applied = await asyncio.to_thread(apply_pending_results, queue, accounts, history)
        if applied == 0:
            await asyncio.sleep(0.5)


if __name__ == "__main__":  # pragma: no cover
    run()
