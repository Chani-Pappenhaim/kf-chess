from config import settings
from protocol.messages import (
    HintsRequest,
    Login,
    MoveRequest,
    Rejected,
    StateUpdate,
    Welcome,
    decode,
    encode,
)
from protocol.state import decode_model
from server.__main__ import build_service
from tests.support import FakeAccountStore


def service(store=None):
    """The real graph the server runs, minus the socket and the real database."""
    return build_service(settings, store=store or FakeAccountStore(settings.STARTING_RATING))


def lines(outbox):
    return [line for _target, line in outbox.drain()]


def admit(game, username, password="pw", send=lambda line: None):
    """Seat one client and return its session plus the decoded reply lines."""
    session, replies = game.admit(encode(Login(username, password)), send)
    return session, [decode(line) for line in replies]


def test_a_tick_advances_the_game_and_sends_the_state():
    engine, outbox, game = service()
    game.tick(settings.MOVE_DURATION)

    assert engine.clock == settings.MOVE_DURATION
    message = decode(lines(outbox)[-1])
    assert isinstance(message, StateUpdate)
    assert decode_model(message.state).clock == settings.MOVE_DURATION


def test_the_first_to_join_is_white_the_second_black():
    _engine, _outbox, game = service()
    first, _ = admit(game, "dana")
    second, _ = admit(game, "yossi")
    assert (first.color, second.color) == ("w", "b")


def test_a_third_player_is_turned_away():
    _engine, _outbox, game = service()
    admit(game, "dana")
    admit(game, "yossi")
    session, replies = admit(game, "latecomer")
    assert session is None
    assert isinstance(replies[0], Rejected)


def test_admission_answers_with_a_colour_and_the_state():
    _engine, _outbox, game = service()
    _session, replies = admit(game, "dana")
    assert replies[0] == Welcome("w")
    assert isinstance(replies[1], StateUpdate)


def test_an_opening_line_that_is_not_a_login_is_refused():
    _engine, _outbox, game = service()
    session, replies = game.admit(encode(MoveRequest("WPe2e4")), lambda line: None)
    assert session is None and replies == ()


def test_an_unreadable_opening_line_is_refused():
    _engine, _outbox, game = service()
    session, replies = game.admit("not a message at all", lambda line: None)
    assert session is None and replies == ()


def test_a_departed_player_frees_the_seat():
    _engine, _outbox, game = service()
    first, _ = admit(game, "dana")
    game.depart(first)
    again, _ = admit(game, "chani")
    assert again.color == "w"  # the white seat reopened


def test_the_state_carries_the_names_of_who_has_joined():
    _engine, outbox, game = service()
    admit(game, "dana")
    admit(game, "yossi")
    game.tick(settings.MOVE_DURATION)
    state = decode(lines(outbox)[-1])
    assert decode_model(state.state).players == {"w": "dana", "b": "yossi"}


def test_a_session_moves_only_its_own_colour():
    engine, _outbox, game = service()
    black, _ = admit(game, "yossi")  # first joiner here is white...
    black, _ = admit(game, "chani")  # ...so this second one is black

    black.handle(encode(MoveRequest("WPa2a3")))  # a white pawn - not black's
    game.tick(settings.MOVE_DURATION)
    assert engine.render_model().piece_at((6, 0)).token == "wP"  # unmoved

    black.handle(encode(MoveRequest("BPa7a6")))  # black's own pawn
    game.tick(settings.MOVE_DURATION)
    assert engine.render_model().piece_at((2, 0)).token == "bP"  # moved


def test_a_session_answers_hints_for_its_own_pieces():
    _engine, _outbox, game = service()
    sent = []
    white, _ = admit(game, "dana", send=sent.append)
    white.handle(encode(HintsRequest("a2")))
    assert set(decode(sent[0]).targets) == {"a3", "a4"}


def test_an_event_from_play_reaches_the_outbox():
    _engine, outbox, game = service()
    white, _ = admit(game, "dana")

    white.handle(encode(MoveRequest("WPa2a3")))
    game.tick(settings.MOVE_DURATION)

    kinds = [type(decode(line)).__name__ for line in lines(outbox)]
    assert "EventNotice" in kinds


def test_a_new_username_registers_and_is_admitted():
    _engine, _outbox, game = service()
    session, replies = admit(game, "dana", password="secret")
    assert session is not None
    assert replies[0] == Welcome("w")


def test_a_returning_user_with_the_right_password_is_admitted():
    store = FakeAccountStore(settings.STARTING_RATING)
    store.register("dana", "secret")
    _engine, _outbox, game = service(store)
    session, _ = admit(game, "dana", password="secret")
    assert session is not None


def test_a_returning_user_with_the_wrong_password_is_refused():
    store = FakeAccountStore(settings.STARTING_RATING)
    store.register("dana", "secret")
    _engine, _outbox, game = service(store)
    session, replies = admit(game, "dana", password="wrong")
    assert session is None
    assert replies[0] == Rejected(settings.REJECT_WRONG_PASSWORD)


def test_a_wrong_password_does_not_take_a_seat():
    store = FakeAccountStore(settings.STARTING_RATING)
    store.register("dana", "secret")
    _engine, _outbox, game = service(store)
    admit(game, "dana", password="wrong")             # refused
    good, _ = admit(game, "dana", password="secret")  # the seat was never taken
    assert good.color == "w"


def test_the_state_carries_each_players_rating():
    _engine, outbox, game = service()
    admit(game, "dana")
    game.tick(settings.MOVE_DURATION)
    state = decode(lines(outbox)[-1])
    assert decode_model(state.state).ratings == {"w": settings.STARTING_RATING}
