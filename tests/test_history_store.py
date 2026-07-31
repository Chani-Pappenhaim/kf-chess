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
