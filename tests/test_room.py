import pytest

from accounts.store import Account
from config import settings
from protocol.messages import RoomEntered, decode
from protocol.state import decode_model
from server.registry import PlayerRegistry
from server.room import Room
from view.render_model import RenderModel, RenderPiece


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


class FakeSnapshots:
    def __init__(self):
        self.saved = {}

    def save(self, room_id, snapshot):
        self.saved[room_id] = snapshot

    def load(self, room_id):
        return self.saved.get(room_id)

    def delete(self, room_id):
        self.saved.pop(room_id, None)


class FakePieceEngine(FakeEngine):
    """A FakeEngine whose render_model carries one piece, for snapshot tests."""

    def render_model(self):
        return RenderModel(pieces=(RenderPiece("wK", (0, 0)),), width=8, height=8)


def room_with_snapshots():
    engine = FakePieceEngine()
    snapshots = FakeSnapshots()
    return Room("7", engine, PlayerRegistry(settings.COLORS), 8, settings, snapshots), engine, snapshots


def test_the_game_starting_saves_an_immediate_snapshot():
    r, _engine, snapshots = room_with_snapshots()
    r.join(FakeSession("dana"))
    assert "7" not in snapshots.saved   # one player: no game yet
    r.join(FakeSession("yossi"))
    assert "7" in snapshots.saved


def test_a_snapshot_carries_piece_positions_and_seats():
    r, _engine, snapshots = room_with_snapshots()
    r.join(FakeSession("dana", 1300))
    r.join(FakeSession("yossi", 1100))
    snapshot = snapshots.saved["7"]
    assert snapshot["pieces"] == [["wK", [0, 0]]]
    assert snapshot["players"] == {
        "w": {"username": "dana", "rating": 1300, "computer": False},
        "b": {"username": "yossi", "rating": 1100, "computer": False},
    }


def test_the_snapshot_refreshes_on_the_configured_interval_not_every_tick():
    r, _engine, snapshots = room_with_snapshots()
    r.join(FakeSession("dana"))
    r.join(FakeSession("yossi"))
    snapshots.saved.clear()  # drop the join-time snapshot to isolate tick()
    r.tick(settings.ROOM_SNAPSHOT_INTERVAL_MS - 1)
    assert "7" not in snapshots.saved
    r.tick(1)
    assert "7" in snapshots.saved


def test_no_snapshots_configured_is_a_quiet_no_op():
    r, _engine = room()  # the plain factory passes no snapshots store
    r.join(FakeSession("dana"))
    r.join(FakeSession("yossi"))
    r.tick(settings.ROOM_SNAPSHOT_INTERVAL_MS)  # must not raise


# -- throttled, dirty-flagged broadcasting (server/room.py::tick) ------------

class FakeMovingEngine(FakeEngine):
    """A FakeEngine whose render_model changes on its second call onward, so
    a test can force a genuine dirty-check difference between two ticks."""

    def __init__(self):
        super().__init__()
        self.calls = 0

    def render_model(self):
        self.calls += 1
        cell = (0, 0) if self.calls < 2 else (0, 1)
        return RenderModel(pieces=(RenderPiece("wK", cell),), width=8, height=8)


def test_a_tick_below_the_throttle_interval_sends_nothing():
    r, _ = room()
    white = FakeSession("dana")
    r.join(white)
    white.sent.clear()
    r.tick(settings.STATE_BROADCAST_MS - 1)
    assert white.sent == []


def test_an_unchanged_state_is_not_rebroadcast_even_past_the_throttle():
    # join() already sent the current (idle) state; nothing moves afterward,
    # so the very next throttled tick must stay silent.
    r, _ = room()
    white = FakeSession("dana")
    r.join(white)
    white.sent.clear()
    r.tick(settings.STATE_BROADCAST_MS)
    assert white.sent == []


def test_a_changed_state_is_broadcast_once_the_throttle_interval_passes():
    engine = FakeMovingEngine()
    r = Room("7", engine, PlayerRegistry(settings.COLORS), 8, settings)
    white = FakeSession("dana")
    r.join(white)                              # sends cell (0, 0)
    white.sent.clear()
    r.tick(settings.STATE_BROADCAST_MS)        # render_model now differs -> sends
    assert len(white.sent) == 1
    assert last_state(white).pieces[0].cell == (0, 1)


def test_the_clock_alone_changing_does_not_count_as_dirty():
    # FakeEngine.render_model() never changes its own fields, but the real
    # engine's `clock` always advances - the dirty check must ignore it, or
    # every single tick would count as "changed" and defeat the throttle.
    r, _ = room()
    white = FakeSession("dana")
    r.join(white)
    white.sent.clear()
    r.tick(settings.STATE_BROADCAST_MS)
    r.tick(settings.STATE_BROADCAST_MS)
    assert white.sent == []


# -- a seat held by the computer -------------------------------------------

class FakeComputer:
    """Records the time it was given, as a ComputerPlayer would spend it."""

    def __init__(self, color):
        self.color = color
        self.ticked = 0

    def tick(self, dt):
        self.ticked += dt


def computer_room(registry=None):
    built = {}

    def factory(color):
        built[color] = FakeComputer(color)
        return built[color]

    engine = FakeEngine()
    registry = registry or PlayerRegistry(settings.COLORS)
    return Room("7", engine, registry, 8, settings, computer_factory=factory), engine, built


def test_the_computer_takes_the_colour_it_is_given_and_the_human_the_other():
    r, _, _ = computer_room()
    assert r.add_computer("w")
    human = FakeSession("dana")
    r.join(human)
    assert human.color == "b"


def test_the_computer_is_shown_under_its_configured_name_and_rating():
    r, _, _ = computer_room()
    r.add_computer("b")
    human = FakeSession("dana")
    r.join(human)
    model = last_state(human)
    assert model.players["b"] == settings.COMPUTER_NAME
    assert model.ratings["b"] == settings.COMPUTER_RATING


def test_a_human_joining_the_computer_starts_the_game():
    r, engine, _ = computer_room()
    r.add_computer("b")
    r.join(FakeSession("dana"))
    assert engine.started


def test_the_computer_cannot_take_a_seat_already_held():
    r, _, built = computer_room()
    r.join(FakeSession("dana"))           # takes White
    assert not r.add_computer("w")
    assert "w" not in built
    assert r.add_computer("b")


def test_a_room_built_without_a_computer_player_refuses_to_seat_one():
    r, _ = room()
    with pytest.raises(RuntimeError):
        r.add_computer("b")


def test_the_computer_plays_only_once_the_game_is_on():
    r, _, built = computer_room()
    r.add_computer("b")
    r.tick(100)
    assert built["b"].ticked == 0     # no human yet: nothing to play against
    r.join(FakeSession("dana"))
    r.tick(100)
    assert built["b"].ticked == 100


def test_the_computer_waits_while_its_opponent_is_away():
    r, _, built = computer_room()
    r.add_computer("b")
    human = FakeSession("dana")
    r.join(human)
    r.leave(human)
    r.tick(100)
    assert built["b"].ticked == 0


def test_a_room_whose_human_left_is_kept_until_the_grace_runs_out():
    r, engine, _ = computer_room()
    r.add_computer("b")
    human = FakeSession("dana")
    r.join(human)
    r.leave(human)
    assert not r.is_empty
    r.tick(settings.DISCONNECT_GRACE_MS)
    assert engine.conceded == ("b", settings.GAME_END_FORFEIT)
    assert r.is_empty


def test_a_human_who_rejoins_the_computer_in_time_keeps_their_seat():
    r, engine, built = computer_room()
    r.add_computer("b")
    first = FakeSession("dana")
    r.join(first)
    r.leave(first)
    back = FakeSession("dana")
    r.join(back)
    assert back.color == "w"
    r.tick(settings.DISCONNECT_GRACE_MS)
    assert engine.conceded is None
    assert built["b"].ticked == settings.DISCONNECT_GRACE_MS


def test_a_human_named_like_the_computer_is_not_handed_its_seat():
    r, _, _ = computer_room()
    r.add_computer("b")
    r.join(FakeSession("dana"))
    impostor = FakeSession(settings.COMPUTER_NAME)
    r.join(impostor)
    assert impostor.color is None      # a viewer, not the computer's seat


def test_the_snapshot_marks_the_computer_seat():
    r, _, _ = computer_room()
    r.add_computer("b")
    r.join(FakeSession("dana"))
    players = r.snapshot()["players"]
    assert players["b"]["computer"] is True
    assert players["w"]["computer"] is False


def test_a_rehydrated_room_gets_its_computer_player_back():
    registry = PlayerRegistry(settings.COLORS)
    registry.restore({
        "w": {"username": "dana", "rating": 1200},
        "b": {"username": settings.COMPUTER_NAME, "rating": 1200, "computer": True},
    })
    _, _, built = computer_room(registry)
    assert set(built) == {"b"}


def test_a_snapshot_seating_the_computer_needs_a_room_that_can_build_one():
    registry = PlayerRegistry(settings.COLORS)
    registry.restore({"b": {"username": settings.COMPUTER_NAME, "rating": 1200, "computer": True}})
    with pytest.raises(RuntimeError):
        Room("7", FakeEngine(), registry, 8, settings)
