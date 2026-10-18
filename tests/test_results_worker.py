from server.results_queue import InMemoryResultsQueue
from server.results_worker import process_batch
from tests.support import FakeAccountStore, FakeHistoryStore


class _CommitTrackingQueue(InMemoryResultsQueue):
    """InMemoryResultsQueue plus a counter, so a test can prove
    process_batch actually calls commit() - InMemoryResultsQueue's own
    commit() is a no-op, so nothing else would reveal whether it was called."""

    def __init__(self):
        super().__init__()
        self.commits = 0

    def commit(self):
        self.commits += 1


def test_an_idle_queue_applies_nothing():
    queue = InMemoryResultsQueue()
    assert process_batch(queue, FakeAccountStore(), FakeHistoryStore()) == 0


def test_a_batch_is_committed_once_every_message_in_it_is_applied():
    queue = _CommitTrackingQueue()
    store = FakeAccountStore()
    store.register("dana", "pw")
    queue.publish({"kind": "rating", "username": "dana", "rating": 1216})
    process_batch(queue, store, FakeHistoryStore())
    assert queue.commits == 1


def test_an_idle_poll_does_not_commit():
    # Nothing to commit when nothing was consumed - avoids a pointless
    # round-trip to Kafka every idle poll.
    queue = _CommitTrackingQueue()
    process_batch(queue, FakeAccountStore(), FakeHistoryStore())
    assert queue.commits == 0


def test_a_redelivered_history_message_is_not_recorded_twice():
    # The at-least-once guarantee: the same message (same result_id) arriving
    # twice - e.g. a crash before the offset committed - must not duplicate
    # the row, only the write-that-already-happened repeats harmlessly.
    queue = InMemoryResultsQueue()
    history = FakeHistoryStore()
    payload = {
        "kind": "history", "winner": "dana", "loser": "yossi",
        "reason": None, "at_ms": 1000, "result_id": "game-42",
    }
    queue.publish(payload)
    process_batch(queue, FakeAccountStore(), history)
    queue.publish(dict(payload))  # redelivered: the exact same message again
    process_batch(queue, FakeAccountStore(), history)
    assert len(history.recent("dana", 10)) == 1


def test_a_rating_message_updates_the_account_store():
    queue = InMemoryResultsQueue()
    store = FakeAccountStore()
    store.register("dana", "pw")
    queue.publish({"kind": "rating", "username": "dana", "rating": 1216})
    assert process_batch(queue, store, FakeHistoryStore()) == 1
    assert store.authenticate("dana", "pw").rating == 1216


def test_a_history_message_records_a_game():
    queue = InMemoryResultsQueue()
    history = FakeHistoryStore()
    queue.publish({
        "kind": "history", "winner": "dana", "loser": "yossi",
        "reason": None, "at_ms": 1000,
    })
    process_batch(queue, FakeAccountStore(), history)
    assert history.recent("dana", 10) == ({
        "winner": "dana", "loser": "yossi", "reason": None, "ended_at": 1000,
    },)


def test_a_mixed_batch_applies_every_message():
    queue = InMemoryResultsQueue()
    store = FakeAccountStore()
    store.register("dana", "pw")
    history = FakeHistoryStore()
    queue.publish({"kind": "rating", "username": "dana", "rating": 1216})
    queue.publish({
        "kind": "history", "winner": "dana", "loser": "yossi",
        "reason": None, "at_ms": 1000,
    })
    assert process_batch(queue, store, history) == 2
    assert store.authenticate("dana", "pw").rating == 1216
    assert history.recent("dana", 10) != ()
