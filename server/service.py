"""The whole server as the socket sees it.

What a socket needs and nothing else: advance every game by a tick, admit a
client that has just connected, and let one depart. Keeping these here rather
than inside the socket means the whole of what the server does is testable
without opening a port.

Admission resolves the token an earlier HTTP login was given - login itself is
the API Gateway's job now, not the socket's - and hands back a session that
starts on the home screen.
"""
from __future__ import annotations

from protocol.errors import ProtocolError
from protocol.messages import Connect, Rejected, Welcome, decode, encode
from server.session import ClientSession


class GameService:
    def __init__(self, lobby, matchmaker, tokens, config):
        self._lobby = lobby
        self._matchmaker = matchmaker
        self._tokens = tokens
        self._config = config

    def tick(self, dt):
        """Advance every room and age the matchmaking queue.

        The only place time passes: clients draw what they are sent and never
        advance anything of their own.
        """
        self._lobby.tick(dt)
        self._matchmaker.tick(dt)

    def active_rooms(self):
        """How many games this server is running - the autoscaling signal."""
        return self._lobby.room_count()

    def fleet_active_rooms(self):
        """How many games are running anywhere in the fleet - a dashboard's
        view, distinct from this one process's autoscaling signal."""
        return self._lobby.fleet_room_count()

    def admit(self, opening, send):
        """Resolve a client's opening Connect(token). Returns (session,
        replies): a home-screen session to run, or None when refused, and the
        lines to send it right now. `send` is the queue it answers through."""
        message = self._read_connect(opening)
        if message is None:
            return None, ()
        account = self._tokens.resolve(message.token)
        if account is None:
            return None, (encode(Rejected(self._config.REJECT_INVALID_TOKEN)),)
        session = ClientSession(account, self._lobby, self._matchmaker, send, self._config)
        return session, (encode(Welcome()),)

    def depart(self, session):
        """Free whatever a client held when it disconnects - a queue slot or a
        seat in a room."""
        session.depart()

    def _read_connect(self, opening):
        try:
            message = decode(opening)
        except ProtocolError:
            return None
        return message if isinstance(message, Connect) else None
