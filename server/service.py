"""The game as the socket sees it.

What a socket needs from a game and nothing else: advance it, admit a client
that has just connected, and let one depart. Keeping these here rather than
inside the socket means the whole of what the server does is testable without
opening a port.

Admission is where a connection becomes a player. It reads the opening Login,
authenticates against the account store (registering a new username, or checking
an existing one's password), then takes a colour from the registry - or turns
the client away, with the reason, when the password is wrong or the game is full.
The lines to send in reply travel back with it, so the socket only awaits them.
"""
from __future__ import annotations

from dataclasses import replace

from protocol.errors import ProtocolError
from protocol.messages import Login, Rejected, StateUpdate, Welcome, decode, encode
from protocol.state import encode_model
from server.broadcast import broadcast_state
from server.handler import CommandHandler


class GameService:
    def __init__(self, engine, board_height, outbox, registry, store):
        self._engine = engine
        self._height = board_height
        self._outbox = outbox
        self._registry = registry
        self._store = store

    def tick(self, dt):
        """Advance the game by `dt` and queue the state that results.

        The only place time passes: clients draw what they are sent and never
        advance anything of their own.
        """
        self._engine.wait(dt)
        broadcast_state(
            self._engine, self._registry.names(), self._registry.ratings(),
            self._outbox.to_all,
        )

    def admit(self, opening, send):
        """Seat a client from its opening Login. Returns (session, replies): the
        session to run its commands, or None when refused, and the lines to send
        it right now. `send` is the queue the session answers through in play."""
        login = self._read_login(opening)
        if login is None:
            return None, ()
        account = self._account_for(login)
        if account is None:
            return None, (encode(Rejected("wrong password")),)
        color = self._registry.seat(account)
        if color is None:
            return None, (encode(Rejected("the game already has two players")),)
        session = CommandHandler(self._engine, self._height, send, color)
        return session, (encode(Welcome(color)), self._state_line())

    def depart(self, session):
        """Free a player's colour when they disconnect, so the seat reopens."""
        self._registry.leave(session.color)

    def _account_for(self, login):
        """The account this login is for: a fresh registration for a new name, or
        the matched account for an existing one - None when the password is wrong."""
        if not self._store.exists(login.username):
            return self._store.register(login.username, login.password)
        return self._store.authenticate(login.username, login.password)

    def _read_login(self, opening):
        try:
            message = decode(opening)
        except ProtocolError:
            return None
        return message if isinstance(message, Login) else None

    def _state_line(self):
        model = replace(
            self._engine.render_model(),
            players=self._registry.names(),
            ratings=self._registry.ratings(),
        )
        return encode(StateUpdate(encode_model(model)))
