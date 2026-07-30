"""The WebSocket Gateway: the socket a client actually connects to. It picks a
Game Server for a fresh session, or reconnects to the one a JoinRoom already
names, then relays the rest of the session between the two untouched.
"""
from __future__ import annotations

import asyncio

from websockets.asyncio.client import connect as connect_upstream
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from config import settings
from protocol.messages import JoinRoom, Rejected, decode
from server.room_directory import RedisRoomDirectory


def parse_pool(spec):
    """"id=address,id=address" -> {id: address}."""
    pairs = (entry.split("=", 1) for entry in spec.split(","))
    return {server_id.strip(): address.strip() for server_id, address in pairs}


class WebSocketGateway:  # pragma: no cover - socket shell, exercised by running it
    def __init__(self, config, pool, directory):
        self._config = config
        self._pool = pool
        self._addresses = list(pool.values())
        self._directory = directory
        self._next = 0

    async def run(self):
        async with serve(self._client, self._config.GATEWAY_HOST, self._config.GATEWAY_PORT):
            await asyncio.Future()

    def _pick_address(self):
        address = self._addresses[self._next % len(self._addresses)]
        self._next += 1
        return address

    async def _client(self, client_ws):
        try:
            opening = await client_ws.recv()
        except ConnectionClosed:
            return
        address = self._pick_address()
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
        """The client's first home-screen choice: a JoinRoom naming a room on
        another server reconnects there before it is forwarded."""
        try:
            first = await client_ws.recv()
        except ConnectionClosed:
            return upstream, None
        message = decode(first)
        if isinstance(message, JoinRoom):
            target = self._pool.get(self._directory.get(message.room_id))
            if target is not None and target != address:
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
    directory = RedisRoomDirectory(config.REDIS_URL)
    print(f"KungFu Chess gateway listening on ws://{config.GATEWAY_HOST}:{config.GATEWAY_PORT}")
    asyncio.run(WebSocketGateway(config, pool, directory).run())


if __name__ == "__main__":  # pragma: no cover
    run()
