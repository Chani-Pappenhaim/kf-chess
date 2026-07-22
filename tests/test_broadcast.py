import play
from config import settings
from events.bus import EventBus
from game.events import (
    GameEnded,
    GameStarted,
    JumpStarted,
    MoveCompleted,
    PieceCaptured,
)
from protocol.events import EVENT_TYPES, decode_event
from protocol.messages import EventNotice, StateUpdate, decode
from protocol.state import decode_model
from server.broadcast import broadcast_state, subscribe_broadcast

ONE_OF_EACH = (
    GameStarted(at_ms=0),
    MoveCompleted("wR", (5, 0), (5, 2), None, 1000),
    PieceCaptured("wR", "bP", (5, 2), 1000),
    JumpStarted("wN", (5, 5), 1200),
    GameEnded("w", 1400),
)


def wired():
    """A bus with a broadcaster on it, and the lines it has sent so far."""
    bus, sent = EventBus(), []
    subscribe_broadcast(bus, sent.append)
    return bus, sent


def test_a_published_event_goes_out_as_one_message():
    bus, sent = wired()
    event = PieceCaptured("wR", "bP", (5, 2), 1000)

    bus.publish(event)

    assert len(sent) == 1
    message = decode(sent[0])
    assert isinstance(message, EventNotice)
    assert decode_event(message.event) == event


def test_what_arrives_is_the_event_that_was_published():
    # End to end through the protocol: the client rebuilds the same event the
    # server's engine announced, which is what lets its sound and banner react
    # to a remote game exactly as to a local one.
    bus, sent = wired()
    for event in ONE_OF_EACH:
        bus.publish(event)

    relayed = [decode_event(decode(line).event) for line in sent]
    assert relayed == list(ONE_OF_EACH)


def test_every_event_that_travels_is_relayed():
    # The samples cover the whole vocabulary, so nothing can be added to
    # EVENT_TYPES and quietly go unbroadcast.
    assert {type(event) for event in ONE_OF_EACH} == set(EVENT_TYPES)


def test_a_bus_with_no_broadcaster_sends_nothing():
    # The engine is unchanged by any of this: publishing without a broadcaster
    # subscribed is silent, which is what the local game does.
    bus, sent = EventBus(), []
    bus.publish(GameStarted(at_ms=0))
    assert sent == []


def test_the_state_goes_out_as_one_message():
    engine = play.build_engine(settings)
    sent = []
    broadcast_state(engine, {}, {}, sent.append)

    assert len(sent) == 1
    message = decode(sent[0])
    assert isinstance(message, StateUpdate)
    assert decode_model(message.state) == engine.render_model()


def test_the_names_and_ratings_of_who_is_playing_travel_in_the_state():
    # Names and ratings are the server's, folded into the model at the boundary;
    # the engine's own model carries neither.
    engine = play.build_engine(settings)
    sent = []
    broadcast_state(engine, {"w": "dana"}, {"w": 1516}, sent.append)
    restored = decode_model(decode(sent[0]).state)
    assert restored.ratings == {"w": 1516}


def test_the_names_of_who_is_playing_travel_in_the_state():
    # The names are the server's, folded into the model at the boundary; the
    # engine's own model carries none.
    engine = play.build_engine(settings)
    sent = []
    broadcast_state(engine, {"w": "dana", "b": "yossi"}, {}, sent.append)
    assert decode_model(decode(sent[0]).state).players == {"w": "dana", "b": "yossi"}
