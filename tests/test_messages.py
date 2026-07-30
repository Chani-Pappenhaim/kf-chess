import pytest

import play
from config import settings
from game.events import PieceCaptured
from protocol.errors import ProtocolError
from protocol.events import encode_event
from protocol.messages import (
    Connect,
    CreateRoom,
    EventNotice,
    HintsReply,
    HintsRequest,
    JoinRoom,
    JumpRequest,
    MESSAGE_TYPES,
    MoveRequest,
    NoOpponent,
    Redirected,
    Rejected,
    RoomEntered,
    SeekGame,
    StateUpdate,
    Welcome,
    decode,
    encode,
)
from protocol.state import decode_model, encode_model

SAMPLES = (
    Connect("a-token"),
    MoveRequest("WQe2e5"),
    JumpRequest("e4"),
    HintsRequest("e2"),
    SeekGame(),
    CreateRoom(),
    JoinRoom("7"),
    Welcome(),
    Rejected("full"),
    Redirected("7"),
    RoomEntered("w", "7", False),
    NoOpponent(),
    StateUpdate({"pieces": []}),
    EventNotice({"name": "GameStarted", "fields": {"at_ms": 0}}),
    HintsReply("e2", ("e3", "e4")),
)


@pytest.mark.parametrize("message", SAMPLES)
def test_a_message_survives_the_round_trip_unchanged(message):
    assert decode(encode(message)) == message


def test_every_message_kind_is_covered_by_the_samples():
    # Keeps the round-trip test honest as messages are added.
    assert {type(message) for message in SAMPLES} == set(MESSAGE_TYPES)


def test_what_travels_is_text():
    assert isinstance(encode(JumpRequest("e4")), str)


def test_a_real_state_travels_inside_a_message():
    # The envelope carries the payload without looking inside it: what comes
    # out the far end is the same model that went in.
    model = play.build_engine(settings).render_model()
    restored = decode(encode(StateUpdate(encode_model(model))))
    assert decode_model(restored.state) == model


def test_a_real_event_travels_inside_a_message():
    event = PieceCaptured("wR", "bP", (5, 2), 1000)
    restored = decode(encode(EventNotice(encode_event(event))))
    assert restored.event["name"] == "PieceCaptured"


def test_hint_squares_come_back_as_a_tuple():
    assert decode(encode(HintsReply("e2", ("e3",)))).targets == ("e3",)


def test_text_that_is_not_json_is_refused():
    with pytest.raises(ProtocolError):
        decode("not json at all")


def test_json_that_is_not_a_message_is_refused():
    with pytest.raises(ProtocolError):
        decode("[1, 2, 3]")


def test_a_message_kind_that_does_not_travel_is_refused():
    with pytest.raises(ProtocolError):
        decode('{"name": "DropTables", "fields": {}}')
