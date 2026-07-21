import play
from config import settings
from events.bus import EventBus
from ui.composition import board_origin, build_loop
from ui.game_loop import GameLoop


class _FakeWindow:
    """Stands in for the cv2 window: build_loop only stores it."""

    def show(self, canvas):
        pass

    def poll_events(self):
        return []


def test_the_same_wiring_serves_any_gateway():
    # Handed an engine here; the networked client hands it a NetworkGateway,
    # and nothing else about the window differs.
    bus = EventBus()
    engine, controller = play.build_game(settings, bus)
    loop = build_loop(_FakeWindow(), engine, controller, bus, settings)
    assert isinstance(loop, GameLoop)


def test_the_wired_loop_can_draw_a_frame():
    bus = EventBus()
    engine, controller = play.build_game(settings, bus)
    loop = build_loop(_FakeWindow(), engine, controller, bus, settings)
    assert loop.tick(settings.MOVE_DURATION) is True


def test_the_board_origin_is_where_the_frame_leaves_room_for_it():
    assert board_origin(settings) == (settings.BOARD_ORIGIN_X, settings.BOARD_ORIGIN_Y)
