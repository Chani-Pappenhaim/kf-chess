from game.move_log import MoveLog, MoveRecord


def test_records_are_kept_in_order():
    log = MoveLog()
    log.record("w", "e2-e4", 1000)
    log.record("b", "e7-e5", 2000)

    assert log.entries() == (
        MoveRecord("w", "e2-e4", 1000),
        MoveRecord("b", "e7-e5", 2000),
    )


def test_entries_can_be_filtered_by_color():
    log = MoveLog()
    log.record("w", "e2-e4", 1000)
    log.record("b", "e7-e5", 2000)
    log.record("w", "Ng1-f3", 3000)

    assert log.entries("w") == (
        MoveRecord("w", "e2-e4", 1000),
        MoveRecord("w", "Ng1-f3", 3000),
    )
    assert log.entries("b") == (MoveRecord("b", "e7-e5", 2000),)


def test_a_fresh_log_is_empty():
    assert MoveLog().entries() == ()
