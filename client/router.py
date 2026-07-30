"""Puts each message the server sends where it belongs.

The mirror of the server's CommandHandler: which message does what is a lookup,
not a chain of tests, so a new message is an entry here and a method beside it.
The welcome and room placement update the identity; a state or a hint goes to
the inbox; an event is republished on the client's own bus, which is what lets
sound and animation react to a remote game with no idea that it is one - they are
the same subscribers, on the same kind of bus.
"""
from __future__ import annotations

from protocol.errors import ProtocolError
from protocol.events import decode_event
from protocol.messages import (
    EventNotice,
    HintsReply,
    NoOpponent,
    Redirected,
    Rejected,
    RoomEntered,
    StateUpdate,
    Welcome,
    decode,
)
from protocol.state import decode_model


class MessageRouter:
    def __init__(self, inbox, bus, identity):
        self._inbox = inbox
        self._bus = bus
        self._identity = identity
        self._actions = {
            Welcome: self._welcome,
            Rejected: self._rejected,
            RoomEntered: self._entered,
            NoOpponent: self._no_opponent,
            Redirected: self._redirected,
            StateUpdate: self._state,
            EventNotice: self._event,
            HintsReply: self._hints,
        }

    def route(self, text):
        """Deliver one line from the server.

        Raises ProtocolError on anything unreadable or on a message only a
        client is supposed to send, so a bad line can never be mistaken for
        news about the game.
        """
        message = decode(text)
        action = self._actions.get(type(message))
        if action is None:
            raise ProtocolError(type(message).__name__)
        action(message)

    def _welcome(self, _message):
        self._identity.welcome()

    def _rejected(self, message):
        self._identity.reject(message.reason)

    def _entered(self, message):
        self._identity.entered(message.color, message.room_id, message.spectator)

    def _no_opponent(self, _message):
        self._identity.search_failed()

    def _redirected(self, message):
        self._identity.redirected(message.room_id)

    def _state(self, message):
        self._inbox.receive_state(decode_model(message.state))

    def _event(self, message):
        self._bus.publish(decode_event(message.event))

    def _hints(self, message):
        self._inbox.receive_hints(message.square, message.targets)
