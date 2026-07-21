"""Relays published events to connected clients.

One more subscriber on the game's bus, alongside the move log and the score.
The engine gains nothing and knows nothing: what makes a game networked is a
subscription, not a change to how the game is played.

`send` is injected - a plain callable taking one line of text - so nothing here
knows what a socket is.
"""
from __future__ import annotations

from protocol.events import EVENT_TYPES, encode_event
from protocol.messages import EventNotice, encode


def subscribe_broadcast(bus, send):
    """Relay every event that travels onto `send`.

    Driven by EVENT_TYPES, so an event that becomes sendable is broadcast
    without this being touched.
    """
    def relay(event):
        send(encode(EventNotice(encode_event(event))))

    for event_type in EVENT_TYPES:
        bus.subscribe(event_type, relay)
