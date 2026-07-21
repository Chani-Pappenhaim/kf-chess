import json
from dataclasses import is_dataclass

import pytest

import game.events
from game.events import (
    GameStarted,
    MoveCompleted,
    PieceCaptured,
    JumpStarted,
    GameEnded,
)
from protocol.errors import ProtocolError
from protocol.events import EVENT_TYPES, decode_event, encode_event

SAMPLES = (
    GameStarted(at_ms=0),
    MoveCompleted("wR", (5, 0), (5, 2), None, 1000),
    MoveCompleted("wR", (5, 0), (5, 2), "bP", 1000),
    PieceCaptured("wR", "bP", (5, 2), 1000),
    JumpStarted("wN", (5, 5), 1200),
    GameEnded("w", 1400),
)


@pytest.mark.parametrize("event", SAMPLES)
def test_an_event_survives_the_round_trip_unchanged(event):
    assert decode_event(encode_event(event)) == event


@pytest.mark.parametrize("event", SAMPLES)
def test_an_encoded_event_is_plain_json(event):
    json.dumps(encode_event(event))


def test_cells_come_back_as_tuples():
    # A list would compare unequal to every cell in the rest of the code.
    event = decode_event(encode_event(MoveCompleted("wR", (5, 0), (5, 2), None, 1000)))
    assert isinstance(event.origin, tuple) and isinstance(event.destination, tuple)


def test_an_event_is_labelled_with_its_own_type_name():
    assert encode_event(GameEnded("w", 1400))["name"] == "GameEnded"


def test_every_event_the_game_publishes_can_travel():
    # The drift guard: a new event added to game/events.py has to be listed as
    # travelling, or the client will never hear about it.
    published = [
        value
        for value in vars(game.events).values()
        if isinstance(value, type) and is_dataclass(value)
    ]
    assert set(published) == set(EVENT_TYPES)


def test_an_unknown_event_name_is_refused():
    with pytest.raises(ProtocolError):
        decode_event({"name": "SomethingElse", "fields": {}})


def test_data_with_no_name_at_all_is_refused():
    with pytest.raises(ProtocolError):
        decode_event({})


def test_fields_that_do_not_fit_the_event_are_refused():
    with pytest.raises(ProtocolError):
        decode_event({"name": "GameEnded", "fields": {"nonsense": 1}})


def test_an_event_type_that_does_not_travel_is_refused():
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Private:
        at_ms: int = 0

    with pytest.raises(ProtocolError):
        encode_event(Private())
