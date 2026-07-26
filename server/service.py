"""The whole server as the socket sees it.

What a socket needs and nothing else: advance every game by a tick, admit a
client that has just connected, and let one depart. Keeping these here rather
than inside the socket means the whole of what the server does is testable
without opening a port.

Admission authenticates against the account store (registering a new username,
or checking an existing one's password) and hands back a session that starts on
the home screen. Which game it ends up in - a quick match, a room it opened, a
room it joined - is the session's own story from there; the service only advances
the lobby and the matchmaker on each tick.
"""
from __future__ import annotations

from protocol.errors import ProtocolError
from protocol.messages import Login, Rejected, Welcome, decode, encode
from server.session import ClientSession


class GameService:
    def __init__(self, lobby, matchmaker, store, config):
        self._lobby = lobby
        self._matchmaker = matchmaker
        self._store = store
        self._config = config

    def tick(self, dt):
        """Advance every room and age the matchmaking queue.

        The only place time passes: clients draw what they are sent and never
        advance anything of their own.
        """
        self._lobby.tick(dt)
        self._matchmaker.tick(dt)

    def admit(self, opening, send):
        """Authenticate a client from its opening Login. Returns (session,
        replies): a home-screen session to run, or None when refused, and the
        lines to send it right now. `send` is the queue it answers through."""
        login = self._read_login(opening)
        if login is None:
            return None, ()
        new_account = not self._store.exists(login.username)
        account = self._account_for(login, new_account)
        if account is None:
            return None, (encode(Rejected(self._config.REJECT_WRONG_PASSWORD)),)
        session = ClientSession(account, self._lobby, self._matchmaker, send, self._config)
        return session, (encode(Welcome(new_account)),)

    def depart(self, session):
        """Free whatever a client held when it disconnects - a queue slot or a
        seat in a room."""
        session.depart()

    def _account_for(self, login, new_account):
        if new_account:
            return self._store.register(login.username, login.password)
        return self._store.authenticate(login.username, login.password)

    def _read_login(self, opening):
        try:
            message = decode(opening)
        except ProtocolError:
            return None
        return message if isinstance(message, Login) else None
