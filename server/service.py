"""The game as the socket sees it.

What a socket needs from a game and nothing else: advance it, admit a client
that has just connected, and let one depart. Keeping these here rather than
inside the socket means the whole of what the server does is testable without
opening a port.

Admission is where a connection becomes a player. It reads the opening Login,
takes a colour from the registry, and hands back a session bound to that colour
- or turns the client away when the game is full. The lines to send in reply
travel back with it, so the socket only awaits them; the decision is made here.
"""
from __future__ import annotations

from protocol.errors import ProtocolError
from protocol.messages import Login, Rejected, StateUpdate, Welcome, decode, encode
from protocol.state import encode_model
from server.broadcast import broadcast_state
from server.handler import CommandHandler
from dataclasses import replace


class GameService:
    def __init__(self, engine, board_height, outbox, registry):
        self._engine = engine
        self._height = board_height
        self._outbox = outbox
        self._registry = registry

    def tick(self, dt):
        """Advance the game by `dt` and queue the state that results.

        The only place time passes: clients draw what they are sent and never
        advance anything of their own.
        """
        self._engine.wait(dt)
        broadcast_state(self._engine, self._registry.names(), self._outbox.to_all)

    def admit(self, opening, send):
        """Seat a client from its opening line. Returns (session, replies): the
        session to run its commands, or None when refused, and the lines to send
        it right now. `send` is the queue the session answers through in play."""
        login = self._read_login(opening)
        if login is None:
            return None, ()
        color = self._registry.join(login.username)
        if color is None:
            return None, (encode(Rejected("the game already has two players")),)
        session = CommandHandler(self._engine, self._height, send, color)
        return session, (encode(Welcome(color)), self._state_line())

    def depart(self, session):
        """Free a player's colour when they disconnect, so the seat reopens."""
        self._registry.leave(session.color)

    def _read_login(self, opening):
        try:
            message = decode(opening)
        except ProtocolError:
            return None
        return message if isinstance(message, Login) else None

    def _state_line(self):
        model = replace(self._engine.render_model(), players=self._registry.names())
        return encode(StateUpdate(encode_model(model)))
