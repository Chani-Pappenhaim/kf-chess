"""What the server sends out: the state to draw, and the events as they happen.

Relaying events is one more subscriber on the game's bus, alongside the move log
and the score. The engine gains nothing and knows nothing: what makes a game
networked is a subscription, not a change to how the game is played.

`send` is injected everywhere here - a plain callable taking one line of text -
so nothing in this module knows what a socket is.
"""
from __future__ import annotations

from dataclasses import replace

from protocol.events import EVENT_TYPES, encode_event
from protocol.messages import EventNotice, StateUpdate, encode
from protocol.state import encode_model


def subscribe_broadcast(bus, send):
    """Relay every event that travels onto `send`.

    Driven by EVENT_TYPES, so an event that becomes sendable is broadcast
    without this being touched.
    """
    def relay(event):
        send(encode(EventNotice(encode_event(event))))

    for event_type in EVENT_TYPES:
        bus.subscribe(event_type, relay)


def broadcast_state(engine, players, send):
    """Send the whole state as it stands right now.

    The player names are the server's, not the engine's, so they are folded into
    the model here at the boundary rather than inside a game that has no notion
    of players. Whole state, not the difference from last time: a client that
    misses one is corrected by the next, and one just connected needs no catching
    up beyond a single line.
    """
    model = replace(engine.render_model(), players=players)
    send(encode(StateUpdate(encode_model(model))))
