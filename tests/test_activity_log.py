from logs.activity_log import ActivityLog, silent_log


def test_a_sent_line_is_recorded_as_sent():
    out = []
    ActivityLog(out.append).sent("hello")
    assert out == ["sent hello"]


def test_a_received_line_is_recorded_as_received():
    out = []
    ActivityLog(out.append).received("hello")
    assert out == ["recv hello"]


def test_a_note_is_recorded_as_written():
    out = []
    ActivityLog(out.append).note("connected")
    assert out == ["connected"]


def test_a_silent_log_keeps_nothing_and_does_not_fail():
    log = silent_log()
    log.sent("x")
    log.received("y")
    log.note("z")  # the point is simply that none of these raise
