import pytest

import play
from client.identity import Identity
from client.inbox import Inbox
from client.router import MessageRouter
from config import settings
from events.bus import EventBus
from game.events import MoveCompleted, PieceCaptured
from protocol.errors import ProtocolError
from protocol.events import encode_event
from protocol.messages import (
    EventNotice,
    HintsReply,
    MoveRequest,
    Rejected,
    StateUpdate,
    Welcome,
    encode,
)
from protocol.state import encode_model


def routed():
    inbox, bus, identity = Inbox(), EventBus(), Identity()
    return inbox, bus, identity, MessageRouter(inbox, bus, identity)


def test_a_state_message_becomes_the_model_to_draw():
    inbox, _bus, _id, router = routed()
    model = play.build_engine(settings).render_model()

    router.route(encode(StateUpdate(encode_model(model))))

    assert inbox.model() == model


def test_an_event_message_is_republished_on_the_client_bus():
    # The whole point: the same event object the server's engine announced now
    # exists on this client's bus, so the same subscribers react to it.
    inbox, bus, _id, router = routed()
    seen = []
    bus.subscribe(PieceCaptured, seen.append)
    event = PieceCaptured("wR", "bP", (5, 2), 1000)

    router.route(encode(EventNotice(encode_event(event))))

    assert seen == [event]


def test_each_event_reaches_only_its_own_subscribers():
    _inbox, bus, _id, router = routed()
    captures, moves = [], []
    bus.subscribe(PieceCaptured, captures.append)
    bus.subscribe(MoveCompleted, moves.append)

    router.route(encode(EventNotice(encode_event(
        MoveCompleted("wR", (5, 0), (5, 2), None, 1000)
    ))))

    assert moves and captures == []


def test_a_hints_message_becomes_an_answer_about_that_square():
    inbox, _bus, _id, router = routed()
    router.route(encode(HintsReply("e2", ("e3", "e4"))))
    assert inbox.hints("e2") == ("e3", "e4")


def test_a_message_only_a_client_sends_is_refused():
    _inbox, _bus, _id, router = routed()
    with pytest.raises(ProtocolError):
        router.route(encode(MoveRequest("WQe2e5")))


def test_text_that_is_not_a_message_is_refused():
    _inbox, _bus, _id, router = routed()
    with pytest.raises(ProtocolError):
        router.route("nonsense")


def test_a_welcome_tells_this_client_its_colour():
    _inbox, _bus, identity, router = routed()
    router.route(encode(Welcome("b")))
    assert identity.color() == "b"
    assert identity.new_account() is False  # the default when the flag is unset


def test_a_welcome_says_whether_the_login_created_the_account():
    _inbox, _bus, identity, router = routed()
    router.route(encode(Welcome("w", True)))
    assert identity.new_account() is True


def test_a_rejection_is_recorded_with_its_reason_so_the_client_can_give_up():
    _inbox, _bus, identity, router = routed()
    router.route(encode(Rejected("wrong password")))
    assert identity.rejected() is True
    assert identity.rejection_reason() == "wrong password"
