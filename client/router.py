"""Puts each message the server sends where it belongs.

The mirror of the server's CommandHandler: which message does what is a lookup,
not a chain of tests, so a new message is an entry here and a method beside it.

An event is republished on the client's own bus rather than handled here, which
is what lets sound and animation react to a remote game with no idea that it is
one - they are the same subscribers, on the same kind of bus.
"""
from __future__ import annotations

from protocol.errors import ProtocolError
from protocol.events import decode_event
from protocol.messages import EventNotice, HintsReply, StateUpdate, decode
from protocol.state import decode_model


class MessageRouter:
    def __init__(self, inbox, bus):
        self._inbox = inbox
        self._bus = bus
        self._actions = {
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

    def _state(self, message):
        self._inbox.receive_state(decode_model(message.state))

    def _event(self, message):
        self._bus.publish(decode_event(message.event))

    def _hints(self, message):
        self._inbox.receive_hints(message.square, message.targets)
