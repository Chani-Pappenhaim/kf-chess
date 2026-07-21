"""The game as the socket sees it.

Three things a socket needs from a game and nothing else: advance it, greet a
client that has just connected, and hand each connection something to take its
commands. Keeping them here rather than inside the socket means the whole of
what the server does is testable without opening a port.
"""
from __future__ import annotations

from server.broadcast import broadcast_state
from server.handler import CommandHandler


class GameService:
    def __init__(self, engine, board_height, outbox):
        self._engine = engine
        self._height = board_height
        self._outbox = outbox

    def tick(self, dt):
        """Advance the game by `dt` and queue the state that results.

        The only place time passes: clients draw what they are sent and never
        advance anything of their own.
        """
        self._engine.wait(dt)
        broadcast_state(self._engine, self._outbox.to_all)

    def greet(self, send):
        """What a client is told the instant it connects: the state, so that
        joining midway needs no catching up."""
        broadcast_state(self._engine, send)

    def session_for(self, send):
        """Something to take one client's commands, answering back down `send`."""
        return CommandHandler(self._engine, self._height, send)
