from config import settings
from protocol.messages import HintsRequest, MoveRequest, StateUpdate, decode, encode
from protocol.state import decode_model
from server.__main__ import build_service
from server.outbox import Outbox
from server.service import GameService


def service():
    """The real graph the server runs, minus the socket."""
    return build_service(settings)


def lines(outbox):
    return [line for _target, line in outbox.drain()]


def test_a_tick_advances_the_game_and_sends_the_state():
    engine, outbox, game = service()
    game.tick(settings.MOVE_DURATION)

    assert engine.clock == settings.MOVE_DURATION
    message = decode(lines(outbox)[-1])
    assert isinstance(message, StateUpdate)
    assert decode_model(message.state).clock == settings.MOVE_DURATION


def test_a_client_is_greeted_with_the_state():
    engine, outbox, game = service()
    replies = []
    game.greet(replies.append)

    assert decode_model(decode(replies[0]).state) == engine.render_model()


def test_a_greeting_goes_only_to_the_client_that_arrived():
    _engine, outbox, game = service()
    game.greet(lambda line: None)
    assert lines(outbox) == []


def test_a_session_drives_the_real_engine():
    engine, _outbox, game = service()
    session = game.session_for(lambda line: None)

    session.handle(encode(MoveRequest("WPa2a3")))   # a1 rank is white's home
    game.tick(settings.MOVE_DURATION)

    assert engine.render_model().piece_at((5, 0)).token == "wP"


def test_a_session_answers_hints_from_the_real_rules():
    _engine, _outbox, game = service()
    replies = []
    session = game.session_for(replies.append)

    session.handle(encode(HintsRequest("a2")))

    assert set(decode(replies[0]).targets) == {"a3", "a4"}  # one step or two


def test_an_event_from_play_reaches_the_outbox():
    # The whole chain in one: a command moves a piece, the arrival publishes an
    # event, the broadcaster encodes it, and it is queued for every client.
    _engine, outbox, game = service()
    session = game.session_for(lambda line: None)

    session.handle(encode(MoveRequest("WPa2a3")))
    game.tick(settings.MOVE_DURATION)

    kinds = [type(decode(line)).__name__ for line in lines(outbox)]
    assert "EventNotice" in kinds


def test_the_service_needs_nothing_but_what_it_is_given():
    # No socket, no port, no network of any kind is involved in any of this.
    engine, outbox, _game = service()
    assert isinstance(outbox, Outbox)
    assert isinstance(GameService(engine, 8, Outbox()), GameService)
