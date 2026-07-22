from accounts.store import Account
from config import settings
from events.bus import EventBus
from game.events import GameEnded, MoveCompleted
from server.ratings import subscribe_ratings
from server.registry import PlayerRegistry
from tests.support import FakeAccountStore

K = settings.ELO_K_FACTOR


def wired(white_rating=1200, black_rating=1200):
    """A bus with the rating subscriber on it, over two seated players."""
    bus = EventBus()
    store = FakeAccountStore()
    registry = PlayerRegistry(settings.COLORS)
    store.register("dana", "pw"); store.set_rating("dana", white_rating)
    store.register("yossi", "pw"); store.set_rating("yossi", black_rating)
    registry.seat(Account("dana", white_rating))    # white
    registry.seat(Account("yossi", black_rating))   # black
    subscribe_ratings(bus, registry, store, settings)
    return bus, registry, store


def test_the_winner_gains_and_the_loser_loses():
    bus, registry, store = wired(1200, 1200)
    bus.publish(GameEnded(winner="w", at_ms=1000))
    assert registry.ratings() == {"w": 1216, "b": 1184}


def test_the_new_ratings_are_persisted_to_the_store():
    bus, _registry, store = wired(1200, 1200)
    bus.publish(GameEnded(winner="b", at_ms=1000))
    # Black won, so black's stored rating rose and white's fell.
    assert store.authenticate("yossi", "pw").rating == 1216
    assert store.authenticate("dana", "pw").rating == 1184


def test_beating_a_higher_rated_player_gains_more():
    bus, registry, _store = wired(white_rating=1200, black_rating=1600)
    bus.publish(GameEnded(winner="w", at_ms=1000))
    assert registry.ratings()["w"] - 1200 > 16  # more than an even-match win


def test_only_game_ended_moves_ratings():
    bus, registry, _store = wired(1200, 1200)
    bus.publish(MoveCompleted("wR", (5, 0), (5, 2), None, 1000))
    assert registry.ratings() == {"w": 1200, "b": 1200}


def test_a_game_with_an_empty_seat_moves_nothing():
    # No opponent to rate against: a win with only one player seated is a no-op.
    bus = EventBus()
    store = FakeAccountStore()
    registry = PlayerRegistry(settings.COLORS)
    store.register("dana", "pw")
    registry.seat(Account("dana", 1200))  # white only
    subscribe_ratings(bus, registry, store, settings)

    bus.publish(GameEnded(winner="w", at_ms=1000))
    assert registry.ratings() == {"w": 1200}
