import os
import tempfile
import threading

from accounts.history_store import HistoryStore, SqliteHistoryStore


def store():
    """A throwaway database in memory - a real SqliteHistoryStore, no file."""
    return SqliteHistoryStore(":memory:")


def test_it_satisfies_the_history_store_contract():
    assert isinstance(store(), HistoryStore)


def test_a_fresh_player_has_no_history():
    assert store().recent("dana", 10) == ()


def test_a_recorded_game_is_returned_for_the_winner():
    db = store()
    db.record("dana", "yossi", None, 1000)
    assert db.recent("dana", 10) == ({
        "winner": "dana", "loser": "yossi", "reason": None, "ended_at": 1000,
    },)


def test_a_recorded_game_is_returned_for_the_loser_too():
    db = store()
    db.record("dana", "yossi", None, 1000)
    assert db.recent("yossi", 10) == ({
        "winner": "dana", "loser": "yossi", "reason": None, "ended_at": 1000,
    },)


def test_a_third_player_sees_none_of_it():
    db = store()
    db.record("dana", "yossi", None, 1000)
    assert db.recent("chani", 10) == ()


def test_most_recent_first():
    db = store()
    db.record("dana", "yossi", None, 1000)
    db.record("yossi", "dana", None, 2000)
    assert [g["ended_at"] for g in db.recent("dana", 10)] == [2000, 1000]


def test_the_limit_caps_how_many_come_back():
    db = store()
    for i in range(5):
        db.record("dana", "yossi", None, i)
    assert len(db.recent("dana", 2)) == 2


def test_a_forfeit_reason_is_kept():
    db = store()
    db.record("dana", "yossi", "forfeit", 1000)
    assert db.recent("dana", 10)[0]["reason"] == "forfeit"


def test_a_repeated_result_id_is_not_recorded_twice():
    # The idempotency guarantee server/results_worker.py relies on: the same
    # result_id (a redelivered at-least-once message) must not duplicate the row.
    db = store()
    db.record("dana", "yossi", None, 1000, result_id="game-1")
    db.record("dana", "yossi", None, 1000, result_id="game-1")
    assert len(db.recent("dana", 10)) == 1


def test_two_different_result_ids_are_both_recorded():
    db = store()
    db.record("dana", "yossi", None, 1000, result_id="game-1")
    db.record("dana", "yossi", None, 2000, result_id="game-2")
    assert len(db.recent("dana", 10)) == 2


def test_no_result_id_still_records_normally():
    # Direct/local callers with nothing to dedupe against (no queue in front
    # of them) can omit it - the store mints its own so the column is never
    # NULL, and two omitted calls are still two distinct rows.
    db = store()
    db.record("dana", "yossi", None, 1000)
    db.record("dana", "yossi", None, 2000)
    assert len(db.recent("dana", 10)) == 2


def test_concurrent_recordings_from_many_threads_all_land():
    # Same real concurrency hazard the load test found in SqliteAccountStore:
    # /history and game-end recording can both hit this from different
    # ThreadingHTTPServer / event-loop threads sharing one connection.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = SqliteHistoryStore(path)
        errors = []

        def record(i):
            try:
                db.record(f"winner-{i}", f"loser-{i}", None, i)
            except Exception as error:  # noqa: BLE001 - any exception here is the bug
                errors.append(error)

        threads = [threading.Thread(target=record, args=(i,)) for i in range(100)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        assert all(db.recent(f"winner-{i}", 10) for i in range(100))
    finally:
        db._db.close()
        os.remove(path)
