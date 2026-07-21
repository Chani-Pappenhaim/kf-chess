"""Game events as plain data, and back.

The very events the engine publishes on its bus, in the form that crosses the
wire. A client republishes whatever arrives onto its own bus, so sound and
animation react to a remote game exactly as they do to a local one.

EVENT_TYPES is the list of events that travel. Adding to it is how a new event
becomes something clients hear about; leaving one out keeps it internal.
"""
from __future__ import annotations

from game.events import (
    GameStarted,
    MoveCompleted,
    PieceCaptured,
    JumpStarted,
    GameEnded,
)
from protocol.records import by_name, decode_record, encode_record

EVENT_TYPES = (GameStarted, MoveCompleted, PieceCaptured, JumpStarted, GameEnded)

_ALLOWED = by_name(EVENT_TYPES)


def encode_event(event):
    """A published event as plain data."""
    return encode_record(event, _ALLOWED)


def decode_event(data):
    """Plain data back into the event it names."""
    return decode_record(data, _ALLOWED)
