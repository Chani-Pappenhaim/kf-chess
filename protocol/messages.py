"""Everything the two sides may say to each other, and how it is written.

Three messages travel each way. A client asks to move, to jump, or for the
squares its selected piece may reach; a server sends the state to draw, an
event that just happened, and the hints it was asked for.

The payloads are already-encoded plain data - this module carries them and does
not look inside, so what a state or an event contains stays the business of
protocol.state and protocol.events.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from protocol.errors import ProtocolError
from protocol.records import by_name, decode_record, encode_record


# -- client to server ------------------------------------------------------

@dataclass(frozen=True)
class Login:
    """The first thing a client says: who is joining. Sent before any command,
    so the server can hand out a colour before it takes orders."""

    username: str


@dataclass(frozen=True)
class MoveRequest:
    """Move a piece. `command` is the wire form built by protocol.commands."""

    command: str


@dataclass(frozen=True)
class JumpRequest:
    """Jump the piece on `square`."""

    square: str


@dataclass(frozen=True)
class HintsRequest:
    """Which squares may the piece on `square` move to? Asked when a player
    picks a piece up, because only the server knows the rules."""

    square: str


# -- server to client ------------------------------------------------------

@dataclass(frozen=True)
class Welcome:
    """The answer to a Login: the colour this client was given. It is the one
    thing a client cannot read off the state, since the state names players but
    not which of them is you."""

    color: str


@dataclass(frozen=True)
class Rejected:
    """The other answer to a Login: no seat was free. The game already has its
    two players."""

    reason: str


@dataclass(frozen=True)
class StateUpdate:
    """The whole game state to draw, from protocol.state.encode_model."""

    state: dict


@dataclass(frozen=True)
class EventNotice:
    """Something that just happened, from protocol.events.encode_event."""

    event: dict


@dataclass(frozen=True)
class HintsReply:
    """The answer to a HintsRequest: the squares that piece may reach."""

    square: str
    targets: tuple


MESSAGE_TYPES = (
    Login,
    MoveRequest,
    JumpRequest,
    HintsRequest,
    Welcome,
    Rejected,
    StateUpdate,
    EventNotice,
    HintsReply,
)

_ALLOWED = by_name(MESSAGE_TYPES)


def encode(message):
    """A message as the text that travels."""
    return json.dumps(encode_record(message, _ALLOWED))


def decode(text):
    """Text off the wire back into the message it names.

    Whatever arrives may be truncated, malformed, or not JSON at all, so a
    reader that catches ProtocolError has covered every way this can fail.
    """
    try:
        data = json.loads(text)
    except ValueError as error:
        raise ProtocolError(text) from error
    if not isinstance(data, dict):
        raise ProtocolError(text)
    return decode_record(data, _ALLOWED)
