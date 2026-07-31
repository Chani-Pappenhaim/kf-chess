from accounts.store import Account
from config import settings
from events.bus import EventBus
from game.events import GameEnded, MoveCompleted
from server.history import subscribe_history
from server.registry import PlayerRegistry
from tests.support import FakeHistoryStore


def wired():
    """A bus with the history subscriber on it, over two seated players."""
    bus = EventBus()
    history = FakeHistoryStore()
    registry = PlayerRegistry(settings.COLORS)
    registry.seat(Account("dana", 1200))    # white
    registry.seat(Account("yossi", 1200))   # black
    subscribe_history(bus, registry, history, settings)
    return bus, registry, history


def test_the_winner_and_loser_are_recorded_by_name():
    bus, _registry, history = wired()
    bus.publish(GameEnded(winner="w", at_ms=1000))
    assert history.recent("dana", 10) == ({
        "winner": "dana", "loser": "yossi", "reason": None, "ended_at": 1000,
    },)


def test_the_reason_travels_with_the_result():
    bus, _registry, history = wired()
    bus.publish(GameEnded(winner="b", at_ms=2000, reason=settings.GAME_END_FORFEIT))
    assert history.recent("yossi", 10)[0]["reason"] == settings.GAME_END_FORFEIT


def test_only_game_ended_records_anything():
    bus, _registry, history = wired()
    bus.publish(MoveCompleted("wR", (5, 0), (5, 2), None, 1000))
    assert history.recent("dana", 10) == ()


def test_a_game_with_an_empty_seat_records_nothing():
    # No opponent to record a result against: a win with only one player
    # seated is a no-op, exactly like ratings.
    bus = EventBus()
    history = FakeHistoryStore()
    registry = PlayerRegistry(settings.COLORS)
    registry.seat(Account("dana", 1200))  # white only
    subscribe_history(bus, registry, history, settings)

    bus.publish(GameEnded(winner="w", at_ms=1000))
    assert history.recent("dana", 10) == ()
