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
class Connect:
    """The first thing a client says: the token an earlier HTTP login was given.
    Sent before any command, so the server can admit the session before it takes
    orders."""

    token: str


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


@dataclass(frozen=True)
class SeekGame:
    """The "Play" button: find me any opponent seeking a game near my rating."""


@dataclass(frozen=True)
class CreateRoom:
    """The "Create" button: open a new room and put me in it as its first
    player. The server answers with the generated room id."""


@dataclass(frozen=True)
class JoinRoom:
    """The "Join" button: put me in the room with this id - as Black if a seat
    is free, or as a viewer once both seats are taken."""

    room_id: str


# -- server to client ------------------------------------------------------

@dataclass(frozen=True)
class Welcome:
    """The token was accepted. The greeting (new account or returning) was
    already shown from the HTTP login reply; this only opens the game socket."""


@dataclass(frozen=True)
class Rejected:
    """The other answer to a Connect: the token did not resolve. A full room
    does not refuse a client - it takes them in as a viewer instead."""

    reason: str


@dataclass(frozen=True)
class RoomEntered:
    """You are in a room now: which room, which colour you play (None for a
    viewer), and whether you are a viewer. The colour is the one thing a client
    cannot read off the state, since the state names players but not which is
    you; the room id is shown on top of the screen."""

    color: str
    room_id: str
    spectator: bool = False


@dataclass(frozen=True)
class NoOpponent:
    """The answer to SeekGame when none was found within the wait: the client
    goes back to the home screen and may seek again."""


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
    Connect,
    MoveRequest,
    JumpRequest,
    HintsRequest,
    SeekGame,
    CreateRoom,
    JoinRoom,
    Welcome,
    Rejected,
    RoomEntered,
    NoOpponent,
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
