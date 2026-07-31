from accounts.store import Account
from config import settings
from protocol.messages import Connect, MoveRequest, Rejected, Welcome, decode, encode
from server.__main__ import build_room, build_service
from server.service import GameService
from server.tokens import InMemoryTokenStore
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


def service(store=None, tokens=None):
    """The real server graph, minus the socket and the real database."""
    _outbox, game = build_service(
        settings,
        store=store or FakeAccountStore(settings.STARTING_RATING),
        tokens=tokens or InMemoryTokenStore(),
    )
    return game


def admit(game, tokens, account):
    """As the API Gateway already logged `account` in: issue it a token, then
    connect with that token."""
    token = tokens.issue(account)
    session, replies = game.admit(encode(Connect(token)), lambda line: None)
    return session, [decode(line) for line in replies]


def test_a_valid_token_is_admitted_and_welcomed():
    tokens = InMemoryTokenStore()
    session, replies = admit(service(tokens=tokens), tokens, Account("dana", settings.STARTING_RATING))
    assert session is not None
    assert replies[0] == Welcome()


def test_an_unknown_token_is_refused():
    session, replies = service().admit(encode(Connect("nope")), lambda line: None)
    assert session is None
    assert decode(replies[0]) == Rejected(settings.REJECT_INVALID_TOKEN)


def test_an_opening_line_that_is_not_a_connect_is_refused():
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

    def room_count(self):
        return 3

    def fleet_room_count(self):
        return 11


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


def test_active_rooms_reports_the_lobbys_count():
    service = GameService(_FakeLobby(), _FakeMatchmaker(), None, settings)
    assert service.active_rooms() == 3


def test_fleet_active_rooms_reports_the_lobbys_fleet_count():
    service = GameService(_FakeLobby(), _FakeMatchmaker(), None, settings)
    assert service.fleet_active_rooms() == 11
