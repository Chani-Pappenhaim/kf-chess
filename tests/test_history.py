from accounts.store import Account
from config import settings
from events.bus import EventBus
from game.events import GameEnded, MoveCompleted
from server.history import subscribe_history
from server.registry import PlayerRegistry
from server.results_queue import InMemoryResultsQueue
from server.results_worker import process_batch
from tests.support import FakeAccountStore, FakeHistoryStore


def wired():
    """A bus with the history subscriber on it, over two seated players, plus
    the queue it publishes to and a fake store to drain it into."""
    bus = EventBus()
    queue = InMemoryResultsQueue()
    history = FakeHistoryStore()
    registry = PlayerRegistry(settings.COLORS)
    registry.seat(Account("dana", 1200))    # white
    registry.seat(Account("yossi", 1200))   # black
    subscribe_history(bus, registry, queue, settings)
    return bus, registry, queue, history


def test_the_winner_and_loser_are_recorded_by_name_once_drained():
    bus, _registry, queue, history = wired()
    bus.publish(GameEnded(winner="w", at_ms=1000))
    assert history.recent("dana", 10) == ()  # not yet applied
    process_batch(queue, FakeAccountStore(), history)
    assert history.recent("dana", 10) == ({
        "winner": "dana", "loser": "yossi", "reason": None, "ended_at": 1000,
    },)


def test_the_reason_travels_with_the_result():
    bus, _registry, queue, history = wired()
    bus.publish(GameEnded(winner="b", at_ms=2000, reason=settings.GAME_END_FORFEIT))
    process_batch(queue, FakeAccountStore(), history)
    assert history.recent("yossi", 10)[0]["reason"] == settings.GAME_END_FORFEIT


def test_only_game_ended_records_anything():
    bus, _registry, queue, history = wired()
    bus.publish(MoveCompleted("wR", (5, 0), (5, 2), None, 1000))
    assert queue.consume() == []


def test_the_published_payload_carries_a_result_id_for_dedup():
    bus, _registry, queue, _history = wired()
    bus.publish(GameEnded(winner="w", at_ms=1000))
    payload = queue.consume()[0]
    assert payload["result_id"]  # non-empty - minted at publish time


def test_two_different_games_get_two_different_result_ids():
    bus, _registry, queue, _history = wired()
    bus.publish(GameEnded(winner="w", at_ms=1000))
    bus.publish(GameEnded(winner="b", at_ms=2000))
    first, second = queue.consume()
    assert first["result_id"] != second["result_id"]


def test_a_game_with_an_empty_seat_records_nothing():
    # No opponent to record a result against: a win with only one player
    # seated is a no-op, exactly like ratings.
    bus = EventBus()
    queue = InMemoryResultsQueue()
    registry = PlayerRegistry(settings.COLORS)
    registry.seat(Account("dana", 1200))  # white only
    subscribe_history(bus, registry, queue, settings)

    bus.publish(GameEnded(winner="w", at_ms=1000))
    assert queue.consume() == []
