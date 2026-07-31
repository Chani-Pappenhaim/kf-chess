from accounts.store import Account
from config import settings
from protocol.messages import RoomEntered, decode
from protocol.state import decode_model
from server.registry import PlayerRegistry
from server.room import Room
from view.render_model import RenderModel


class FakeEngine:
    """A game stripped to what a room drives: start, concede, advance, render."""

    def __init__(self):
        self.started = False
        self.game_over = False
        self.conceded = None
        self.waited = 0

    def start(self):
        self.started = True

    def concede(self, winner, reason):
        self.game_over = True
        self.conceded = (winner, reason)

    def wait(self, dt):
        self.waited += dt

    def render_model(self):
        return RenderModel(pieces=(), width=8, height=8)


class FakeSession:
    def __init__(self, username, rating=1200):
        self.account = Account(username, rating)
        self.color = None
        self.sent = []

    def send(self, line):
        self.sent.append(line)

    def enter_room(self, room, color, engine, height):
        self.color = color


def room():
    engine = FakeEngine()
    return Room("7", engine, PlayerRegistry(settings.COLORS), 8, settings), engine


def replies(session):
    return [decode(line) for line in session.sent]


def last_state(session):
    states = [m for m in replies(session) if not isinstance(m, RoomEntered)]
    return decode_model(states[-1].state)


def test_a_room_knows_its_own_id():
    r, _ = room()
    assert r.id == "7"


def test_the_first_to_join_is_white_the_second_black():
    r, _ = room()
    white, black = FakeSession("dana"), FakeSession("yossi")
    r.join(white)
    r.join(black)
    assert (white.color, black.color) == ("w", "b")


def test_a_joiner_is_told_the_room_its_colour_and_that_it_is_not_a_viewer():
    r, _ = room()
    white = FakeSession("dana")
    r.join(white)
    entered = replies(white)[0]
    assert isinstance(entered, RoomEntered)
    assert (entered.color, entered.room_id, entered.spectator) == ("w", "7", False)


def test_a_third_joiner_is_a_viewer():
    r, _ = room()
    r.join(FakeSession("dana"))
    r.join(FakeSession("yossi"))
    viewer = FakeSession("chani")
    r.join(viewer)
    entered = replies(viewer)[0]
    assert entered.color is None and entered.spectator is True
    assert viewer.color is None


def test_the_watchers_are_listed_in_the_state():
    r, _ = room()
    r.join(FakeSession("dana"))
    r.join(FakeSession("yossi"))
    viewer = FakeSession("chani")
    r.join(viewer)
    assert last_state(viewer).viewers == ("chani",)


def test_the_game_starts_only_once_both_seats_fill():
    r, engine = room()
    r.join(FakeSession("dana"))
    assert engine.started is False       # a lone player is still waiting
    r.join(FakeSession("yossi"))
    assert engine.started is True


def test_a_tick_advances_the_game():
    r, engine = room()
    r.join(FakeSession("dana"))
    r.tick(settings.MOVE_DURATION)
    assert engine.waited == settings.MOVE_DURATION


def test_a_player_leaving_mid_game_resigns_after_the_grace():
    r, engine = room()
    white, black = FakeSession("dana"), FakeSession("yossi")
    r.join(white)
    r.join(black)
    r.leave(black)
    assert engine.game_over is False                 # the grace is still running
    r.tick(settings.DISCONNECT_GRACE_MS)
    assert engine.game_over is True
    assert engine.conceded == ("w", settings.GAME_END_FORFEIT)  # the one who stayed wins


def test_the_remaining_player_sees_the_countdown():
    r, _ = room()
    white, black = FakeSession("dana"), FakeSession("yossi")
    r.join(white)
    r.join(black)
    r.leave(black)
    white.sent.clear()
    r.tick(1000)
    assert last_state(white).countdown == (settings.DISCONNECT_GRACE_MS - 1000) // 1000


def test_a_viewer_leaving_ends_nothing():
    r, engine = room()
    r.join(FakeSession("dana"))
    r.join(FakeSession("yossi"))
    viewer = FakeSession("chani")
    r.join(viewer)
    r.leave(viewer)
    r.tick(settings.DISCONNECT_GRACE_MS * 2)
    assert engine.game_over is False


def test_both_players_leaving_crowns_no_one():
    r, engine = room()
    white, black = FakeSession("dana"), FakeSession("yossi")
    r.join(white)
    r.join(black)
    r.leave(black)   # starts the countdown
    r.leave(white)   # the other left too
    r.tick(settings.DISCONNECT_GRACE_MS)
    assert engine.game_over is False
    assert r.is_empty


def test_a_lone_player_leaving_just_empties_the_room():
    r, engine = room()
    white = FakeSession("dana")
    r.join(white)
    r.leave(white)
    assert r.is_empty
    r.tick(settings.DISCONNECT_GRACE_MS)
    assert engine.game_over is False


def test_a_reconnecting_player_gets_their_own_seat_back_not_a_viewer_seat():
    r, engine = room()
    white, black = FakeSession("dana"), FakeSession("yossi")
    r.join(white)
    r.join(black)
    r.leave(black)                     # starts the resign countdown
    reconnected = FakeSession("yossi")
    r.join(reconnected)
    assert reconnected.color == "b"
    r.tick(settings.DISCONNECT_GRACE_MS)
    assert engine.game_over is False   # the countdown was cancelled, not just outrun


def test_a_reconnecting_player_is_not_told_they_are_a_spectator():
    r, _ = room()
    white, black = FakeSession("dana"), FakeSession("yossi")
    r.join(white)
    r.join(black)
    r.leave(black)
    reconnected = FakeSession("yossi")
    r.join(reconnected)
    entered = replies(reconnected)[0]
    assert (entered.color, entered.spectator) == ("b", False)
