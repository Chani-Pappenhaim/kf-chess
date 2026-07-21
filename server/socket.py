"""The socket itself: the one place websockets and asyncio appear.

A shell, like graphics.Window around cv2 or AudioPlayer around winsound. It
holds the open connections, hands each incoming line to a session, and drains
the outbox onto the wire. It decides nothing about the game, so everything it
is wired to has already been tested without it.

The game stays ordinary blocking code: time is advanced from the tick here, and
anything the game wants to say is queued rather than awaited.
"""
from __future__ import annotations

import asyncio

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from protocol.errors import ProtocolError

_MS_PER_SECOND = 1000  # the game counts in milliseconds, asyncio.sleep in seconds


class WebSocketServer:  # pragma: no cover - socket shell, exercised by running it
    def __init__(self, config, outbox, service):
        self._config = config
        self._outbox = outbox
        self._service = service
        self._clients = set()

    async def run(self):
        host, port = self._config.SERVER_HOST, self._config.SERVER_PORT
        async with serve(self._client, host, port):
            await self._pump()

    async def _client(self, connection):
        """One connection, for as long as it lasts."""
        self._clients.add(connection)

        def send(line):
            self._outbox.to(connection, line)

        self._service.greet(send)
        session = self._service.session_for(send)
        try:
            async for text in connection:
                try:
                    session.handle(text)
                except ProtocolError:
                    # A client that talks nonsense is refused a command, not a
                    # connection: its next line may be perfectly good.
                    pass
        except ConnectionClosed:
            pass
        finally:
            self._clients.discard(connection)

    async def _pump(self):
        """Advance the game and flush what it had to say, forever."""
        interval = self._config.SERVER_TICK_MS
        while True:
            await asyncio.sleep(interval / _MS_PER_SECOND)
            self._service.tick(interval)
            await self._flush()

    async def _flush(self):
        for target, line in self._outbox.drain():
            for client in ((target,) if target is not None else tuple(self._clients)):
                try:
                    await client.send(line)
                except ConnectionClosed:
                    self._clients.discard(client)
