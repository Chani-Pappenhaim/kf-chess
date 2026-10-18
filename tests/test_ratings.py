from accounts.store import Account
from config import settings
from events.bus import EventBus
from game.events import GameEnded, MoveCompleted
from server.ratings import subscribe_ratings
from server.registry import PlayerRegistry
from server.results_queue import InMemoryResultsQueue
from server.results_worker import process_batch
from tests.support import FakeAccountStore, FakeHistoryStore

K = settings.ELO_K_FACTOR


def wired(white_rating=1200, black_rating=1200):
    """A bus with the rating subscriber on it, over two seated players, plus
    the queue it publishes to and a fake store to drain it into."""
    bus = EventBus()
    queue = InMemoryResultsQueue()
    store = FakeAccountStore()
    registry = PlayerRegistry(settings.COLORS)
    store.register("dana", "pw"); store.set_rating("dana", white_rating)
    store.register("yossi", "pw"); store.set_rating("yossi", black_rating)
    registry.seat(Account("dana", white_rating))    # white
    registry.seat(Account("yossi", black_rating))   # black
    subscribe_ratings(bus, registry, queue, settings)
    return bus, registry, queue, store


def test_the_winner_gains_and_the_loser_loses():
    bus, registry, _queue, _store = wired(1200, 1200)
    bus.publish(GameEnded(winner="w", at_ms=1000))
    assert registry.ratings() == {"w": 1216, "b": 1184}


def test_the_new_ratings_reach_the_store_once_the_queue_is_drained():
    bus, _registry, queue, store = wired(1200, 1200)
    bus.publish(GameEnded(winner="b", at_ms=1000))
    # Black won, so black's rating should rise and white's fall - but only
    # once something drains the queue, exactly like the real
    # server/results_worker.py would.
    assert store.authenticate("yossi", "pw").rating == 1200  # not yet applied
    process_batch(queue, store, FakeHistoryStore())
    assert store.authenticate("yossi", "pw").rating == 1216
    assert store.authenticate("dana", "pw").rating == 1184


def test_beating_a_higher_rated_player_gains_more():
    bus, registry, _queue, _store = wired(white_rating=1200, black_rating=1600)
    bus.publish(GameEnded(winner="w", at_ms=1000))
    assert registry.ratings()["w"] - 1200 > 16  # more than an even-match win


def test_only_game_ended_moves_ratings():
    bus, registry, _queue, _store = wired(1200, 1200)
    bus.publish(MoveCompleted("wR", (5, 0), (5, 2), None, 1000))
    assert registry.ratings() == {"w": 1200, "b": 1200}


def test_a_game_with_an_empty_seat_moves_nothing():
    # No opponent to rate against: a win with only one player seated is a no-op.
    bus = EventBus()
    queue = InMemoryResultsQueue()
    registry = PlayerRegistry(settings.COLORS)
    registry.seat(Account("dana", 1200))  # white only
    subscribe_ratings(bus, registry, queue, settings)

    bus.publish(GameEnded(winner="w", at_ms=1000))
    assert registry.ratings() == {"w": 1200}
    assert queue.consume() == []
