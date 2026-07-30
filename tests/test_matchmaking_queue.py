from config import settings
from server.matchmaking_queue import InMemoryMatchmakingQueue


def _queue():
    return InMemoryMatchmakingQueue(settings)


def test_an_empty_queue_has_no_match():
    assert _queue().pop_match(1200) is None


def test_a_seeker_in_range_is_popped_as_a_match_and_removed():
    queue = _queue()
    queue.add("dana", 1200)
    assert queue.pop_match(1250) == "dana"   # within range
    assert queue.pop_match(1250) is None     # and it is gone


def test_a_seeker_out_of_range_is_not_matched():
    queue = _queue()
    queue.add("dana", 1200)
    assert queue.pop_match(1200 + settings.MATCHMAKING_ELO_RANGE + 1) is None


def test_a_removed_seeker_can_no_longer_match():
    queue = _queue()
    queue.add("dana", 1200)
    queue.remove("dana")
    assert queue.pop_match(1200) is None
