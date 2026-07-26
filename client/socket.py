"""The client's socket: the one place websockets and asyncio appear here.

A shell, like server.socket on the other side. It runs on a thread of its own,
because the frame loop is blocking cv2 code that never yields - so the network
cannot live inside it, and the game loop must not have to wait on the network.

The two threads meet in exactly one place, the Inbox. Nothing else is shared,
which is why nothing else needs to be careful.
"""
from __future__ import annotations

import asyncio
import queue
import threading

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from protocol.errors import ProtocolError

_MS_PER_SECOND = 1000
_IDLE_SECONDS = 0.01  # how long the sender naps when there is nothing to send


class WebSocketClient:  # pragma: no cover - socket shell, exercised by running it
    def __init__(self, config, router, log, on_lost):
        self._config = config
        self._router = router
        self._log = log
        self._on_lost = on_lost  # called with a reason when the connection ends
        self._outgoing = queue.Queue()
        self._thread = None

    def start(self):
        """Connect, on a thread that outlives this call.

        A daemon thread: when the window closes the program ends, and a socket
        still waiting for a line must not be what keeps it alive.
        """
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def send(self, line):
        """Queue a line. Called from the frame loop, sent from the socket
        thread, so the game never waits on the network."""
        self._outgoing.put(line)

    def _run(self):
        try:
            asyncio.run(self._talk())
        except OSError:
            # The server was not there to begin with.
            self._on_lost(self._config.SERVER_UNAVAILABLE_TEXT)
        except ConnectionClosed:
            # It went away mid-game. Either way a screen now has a reason to show
            # instead of a window frozen on its last frame.
            self._on_lost(self._config.CONNECTION_LOST_TEXT)

    async def _talk(self):
        async with connect(self._config.SERVER_URL) as connection:
            self._log.note("connected " + self._config.SERVER_URL)
            await asyncio.gather(
                self._receive(connection),
                self._send_queued(connection),
            )

    async def _receive(self, connection):
        async for text in connection:
            self._log.received(text)
            try:
                self._router.route(text)
            except ProtocolError:
                # A line we cannot read is dropped, not fatal: the next state
                # the server sends puts us right again.
                pass

    async def _send_queued(self, connection):
        while True:
            try:
                line = self._outgoing.get_nowait()
            except queue.Empty:
                await asyncio.sleep(_IDLE_SECONDS)
                continue
            self._log.sent(line)
            await connection.send(line)
