"""The WebSocket Gateway: the socket a client actually connects to. Room
placement is a pure hash of the room id (GameAllocator) - the same rule every
Game Server computes for itself, so nothing is stored to look it up. It relays
the rest of a session untouched once it is routed.
"""
from __future__ import annotations

import asyncio

from websockets.asyncio.client import connect as connect_upstream
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from config import settings
from protocol.messages import CreateRoom, JoinRoom, Rejected, decode, encode
from server.allocator import GameAllocator, mint_room_id, parse_pool


def plan_route(message, first, allocator):
    """Where a home-screen choice belongs: (target_server_id, line_to_send).
    A JoinRoom hashes the room it names; a fresh CreateRoom is minted an id and
    hashed the same way; anything else (SeekGame, an already-id'd CreateRoom)
    has no target of its own yet, and stays wherever it already is."""
    if isinstance(message, JoinRoom):
        return allocator.for_key(message.room_id), first
    if isinstance(message, CreateRoom) and not message.room_id:
        room_id = mint_room_id()
        return allocator.for_key(room_id), encode(CreateRoom(room_id))
    return None, first


class WebSocketGateway:  # pragma: no cover - socket shell, exercised by running it
    def __init__(self, config, pool):
        self._config = config
        self._pool = pool
        self._allocator = GameAllocator(pool.keys())

    async def run(self):
        async with serve(self._client, self._config.GATEWAY_HOST, self._config.GATEWAY_PORT):
            await asyncio.Future()

    async def _client(self, client_ws):
        try:
            opening = await client_ws.recv()
        except ConnectionClosed:
            return
        # Any server can authenticate a token; spread these evenly over the pool.
        address = self._pool[self._allocator.for_key(opening)]
        upstream = await connect_upstream(address)
        try:
            await upstream.send(opening)
            reply = await upstream.recv()
            await client_ws.send(reply)
            if isinstance(decode(reply), Rejected):
                return
            upstream, first = await self._route(client_ws, upstream, address, opening)
            if first is None:
                return
            await upstream.send(first)
            await self._relay(client_ws, upstream)
        finally:
            await upstream.close()

    async def _route(self, client_ws, upstream, address, opening):
        """The client's first home-screen choice: a room-bound one (Join, or a
        fresh Create) reconnects to whichever server that room hashes to."""
        try:
            first = await client_ws.recv()
        except ConnectionClosed:
            return upstream, None
        target_id, first = plan_route(decode(first), first, self._allocator)
        if target_id is not None:
            target = self._pool[target_id]
            if target != address:
                await upstream.close()
                upstream = await connect_upstream(target)
                await upstream.send(opening)
                await upstream.recv()  # the Welcome, already sent to the client once
        return upstream, first

    async def _relay(self, client_ws, upstream):
        async def to_upstream():
            async for line in client_ws:
                await upstream.send(line)

        async def to_client():
            async for line in upstream:
                await client_ws.send(line)

        try:
            await asyncio.gather(to_upstream(), to_client())
        except ConnectionClosed:
            pass


def run(config=settings):  # pragma: no cover - runs until interrupted
    pool = parse_pool(config.GAME_SERVERS)
    print(f"KungFu Chess gateway listening on ws://{config.GATEWAY_HOST}:{config.GATEWAY_PORT}")
    asyncio.run(WebSocketGateway(config, pool).run())


if __name__ == "__main__":  # pragma: no cover
    run()
