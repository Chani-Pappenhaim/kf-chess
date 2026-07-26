from accounts.store import Account
from config import settings
from protocol.messages import Login, MoveRequest, Rejected, Welcome, decode, encode
from server.__main__ import build_room, build_service
from server.service import GameService
from tests.support import FakeAccountStore


class _FakeMember:
    def __init__(self, username):
        self.account = Account(username, settings.STARTING_RATING)
        self.color = None
        self.sent = []

    def send(self, line):
        self.sent.append(line)

    def enter_room(self, room, color, engine, height):
        self.color = color


def service(store=None):
    """The real server graph, minus the socket and the real database."""
    _outbox, game = build_service(
        settings, store=store or FakeAccountStore(settings.STARTING_RATING)
    )
    return game


def admit(game, username, password="pw"):
    session, replies = game.admit(encode(Login(username, password)), lambda line: None)
    return session, [decode(line) for line in replies]


def test_a_new_username_is_registered_and_welcomed():
    session, replies = admit(service(), "dana")
    assert session is not None
    assert replies[0] == Welcome(True)  # a fresh account


def test_a_returning_user_with_the_right_password_is_welcomed_back():
    store = FakeAccountStore(settings.STARTING_RATING)
    store.register("dana", "pw")
    session, replies = admit(service(store), "dana")
    assert session is not None
    assert replies[0] == Welcome(False)  # a known account, not new


def test_a_returning_user_with_the_wrong_password_is_refused():
    store = FakeAccountStore(settings.STARTING_RATING)
    store.register("dana", "secret")
    session, replies = admit(service(store), "dana", password="wrong")
    assert session is None
    assert replies[0] == Rejected(settings.REJECT_WRONG_PASSWORD)


def test_an_opening_line_that_is_not_a_login_is_refused():
    session, replies = service().admit(encode(MoveRequest("WPe2e4")), lambda line: None)
    assert session is None and replies == ()


def test_an_unreadable_opening_line_is_refused():
    session, replies = service().admit("not a message at all", lambda line: None)
    assert session is None and replies == ()


def test_the_factory_opens_a_real_room_that_loads_a_board_and_seats_two():
    # Exercises build_room end to end: a fresh board, engine, and registry, so
    # the first joiner is White and the second Black on a real game.
    room = build_room("1", settings, FakeAccountStore(settings.STARTING_RATING))
    white, black = _FakeMember("dana"), _FakeMember("yossi")
    room.join(white)
    room.join(black)
    assert (white.color, black.color) == ("w", "b")


# -- the coordinator's own duties, over fakes -------------------------------

class _FakeLobby:
    def __init__(self):
        self.ticks = []

    def tick(self, dt):
        self.ticks.append(dt)


class _FakeMatchmaker:
    def __init__(self):
        self.ticks = []

    def tick(self, dt):
        self.ticks.append(dt)


class _FakeSession:
    def __init__(self):
        self.departed = False

    def depart(self):
        self.departed = True


def test_a_tick_advances_both_the_lobby_and_the_matchmaker():
    lobby, matchmaker = _FakeLobby(), _FakeMatchmaker()
    GameService(lobby, matchmaker, None, settings).tick(33)
    assert lobby.ticks == [33] and matchmaker.ticks == [33]


def test_departing_lets_the_session_clean_up_after_itself():
    session = _FakeSession()
    GameService(_FakeLobby(), _FakeMatchmaker(), None, settings).depart(session)
    assert session.departed is True
