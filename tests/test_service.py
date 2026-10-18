from concurrent.futures import Future

from accounts.store import Account
from bot.factory import ComputerPlayers
from bot.strategy import GreedyStrategy
from config import settings
from protocol.messages import (
    Connect, MoveRequest, PlayComputer, Rejected, RoomEntered, StateUpdate, Welcome, decode, encode,
)
from protocol.state import decode_model
from server.__main__ import build_room, build_service
from server.results_queue import InMemoryResultsQueue
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
        results_queue=InMemoryResultsQueue(),
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
    room = build_room("1", settings, InMemoryResultsQueue())
    white, black = _FakeMember("dana"), _FakeMember("yossi")
    room.join(white)
    room.join(black)
    assert (white.color, black.color) == ("w", "b")


def test_the_factory_rehydrates_a_real_room_from_a_saved_snapshot():
    # Exercises the rehydration path end to end: a real board built from
    # saved piece positions, not the CSV starting layout, with both seats
    # already filled from the snapshot rather than by a fresh join().
    snapshot = {
        "pieces": [["wK", [7, 4]], ["bK", [0, 4]]],
        "width": 8, "height": 8,
        "players": {
            "w": {"username": "dana", "rating": 1300},
            "b": {"username": "yossi", "rating": 1100},
        },
    }
    room = build_room("1", settings, InMemoryResultsQueue(), snapshot=snapshot)
    reconnected = _FakeMember("dana")
    room.join(reconnected)
    assert reconnected.color == "w"  # recognised from the restored registry, not seated fresh


class _InlineExecutor:
    """Runs the computer's thinking at once, on the calling thread."""

    def submit(self, fn, *args):
        future = Future()
        future.set_result(fn(*args))
        return future


def test_playing_the_computer_seats_it_opposite_and_it_moves_on_its_own():
    # The whole path on the real graph: PlayComputer -> a fresh room with the
    # computer in Black's seat -> the game starts -> the computer moves.
    tokens = InMemoryTokenStore()
    computers = ComputerPlayers(GreedyStrategy(settings.BOT_PIECE_VALUES), _InlineExecutor(), settings)
    _outbox, game = build_service(settings, store=FakeAccountStore(settings.STARTING_RATING),
                                  tokens=tokens, results_queue=InMemoryResultsQueue(),
                                  computers=computers)
    lines = []
    session, _ = game.admit(encode(Connect(tokens.issue(Account("dana", 1200)))), lines.append)
    session.handle(encode(PlayComputer("w")))
    entered = [m for m in map(decode, lines) if isinstance(m, RoomEntered)]
    assert entered[0].color == "w"
    for _ in range(3):
        game.tick(settings.BOT_MOVE_INTERVAL_MS)
    states = [decode_model(m.state) for m in map(decode, lines) if isinstance(m, StateUpdate)]
    assert any(piece.token[0] == "b" and piece.state != "idle"
               for piece in states[-1].pieces)


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
