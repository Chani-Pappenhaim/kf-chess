"""Game events as plain data, and back.

The very events the engine publishes on its bus, in the form that crosses the
wire. A client republishes whatever arrives onto its own bus, so sound and
animation react to a remote game exactly as they do to a local one.

Encoding is driven by each event's own fields, so an event that gains a field
carries it without this module changing. EVENT_TYPES is the exception, and
deliberately so: it is the list of events that travel, and adding to it is how
a new event becomes something clients hear about.
"""
from __future__ import annotations

from dataclasses import fields

from game.events import (
    GameStarted,
    MoveCompleted,
    PieceCaptured,
    JumpStarted,
    GameEnded,
)
from protocol.errors import ProtocolError

EVENT_TYPES = (GameStarted, MoveCompleted, PieceCaptured, JumpStarted, GameEnded)

_BY_NAME = {event_type.__name__: event_type for event_type in EVENT_TYPES}


def encode_event(event):
    """A published event as plain data, labelled with the name of its type."""
    name = type(event).__name__
    if name not in _BY_NAME:
        raise ProtocolError(name)
    return {
        "name": name,
        "fields": {
            field.name: _to_wire(getattr(event, field.name))
            for field in fields(event)
        },
    }


def decode_event(data):
    """Plain data back into the event it names."""
    name = data.get("name")
    event_type = _BY_NAME.get(name)
    if event_type is None:
        raise ProtocolError(name)
    values = {
        field: _from_wire(value)
        for field, value in data.get("fields", {}).items()
    }
    try:
        return event_type(**values)
    except TypeError as error:
        raise ProtocolError(name) from error


def _to_wire(value):
    # Cells are the only tuples an event carries, and JSON has no tuples.
    return list(value) if isinstance(value, tuple) else value


def _from_wire(value):
    return tuple(value) if isinstance(value, list) else value
