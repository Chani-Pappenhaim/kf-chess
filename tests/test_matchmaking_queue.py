from config import settings
from server.matchmaking_queue import InMemoryMatchmakingQueue


def _queue():
    return InMemoryMatchmakingQueue(settings)


def test_an_empty_queue_has_no_match():
    assert _queue().pop_match(1200, "local") is None


def test_a_seeker_in_range_is_popped_as_a_match_and_removed():
    queue = _queue()
    queue.add("dana", 1200, "local")
    assert queue.pop_match(1250, "local") == ("dana", 1200)   # within range
    assert queue.pop_match(1250, "local") is None             # and it is gone


def test_a_seeker_out_of_range_is_not_matched():
    queue = _queue()
    queue.add("dana", 1200, "local")
    assert queue.pop_match(1200 + settings.MATCHMAKING_ELO_RANGE + 1, "local") is None


def test_a_removed_seeker_can_no_longer_match():
    queue = _queue()
    queue.add("dana", 1200, "local")
    queue.remove("dana", "local")
    assert queue.pop_match(1200, "local") is None


def test_regions_are_isolated_even_within_elo_range():
    queue = _queue()
    queue.add("dana", 1200, "eu")
    assert queue.pop_match(1200, "us") is None       # right rating, wrong region
    assert queue.pop_match(1200, "eu") == ("dana", 1200)


def test_removing_a_seeker_only_clears_their_own_region():
    queue = _queue()
    queue.add("dana", 1200, "eu")
    queue.remove("dana", "us")  # no-op: "dana" isn't queued in "us"
    assert queue.pop_match(1200, "eu") == ("dana", 1200)
