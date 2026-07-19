from config import settings
from realtime.real_time_arbiter import ArrivalEvent
from game.move_log import MoveLog
from game.notation import CoordinateNotation
from game.observers import GameObserver, MoveRecorder, CaptureScorer
from game.scoreboard import Scoreboard


def arrival(piece="wR", origin=(5, 0), destination=(5, 2), captured=None, at_ms=1000):
    return ArrivalEvent(
        piece=piece,
        origin=origin,
        destination=destination,
        captured=captured,
        at_ms=at_ms,
    )


def test_move_recorder_logs_the_move_in_notation():
    log = MoveLog()
    MoveRecorder(log, CoordinateNotation(8)).on_event(arrival())
    entry = log.entries("w")[0]
    assert entry.notation == "Ra3-c3"


def test_move_recorder_takes_the_time_from_the_event():
    # The event carries its own timestamp, so the recorder needs no clock.
    log = MoveLog()
    MoveRecorder(log, CoordinateNotation(8)).on_event(arrival(at_ms=4200))
    assert log.entries("w")[0].time_ms == 4200


def test_capture_scorer_awards_the_captured_piece_value():
    scoreboard = Scoreboard(settings.COLORS)
    CaptureScorer(scoreboard, settings.PIECE_VALUES).on_event(arrival(captured="bP"))
    assert scoreboard.score("w") == settings.PIECE_VALUES["P"]
    assert scoreboard.score("b") == 0


def test_capture_scorer_ignores_a_move_without_a_capture():
    scoreboard = Scoreboard(settings.COLORS)
    CaptureScorer(scoreboard, settings.PIECE_VALUES).on_event(arrival(captured=None))
    assert scoreboard.score("w") == 0


def test_capture_scorer_scores_an_unvalued_kind_as_zero():
    scoreboard = Scoreboard(settings.COLORS)
    CaptureScorer(scoreboard, {}).on_event(arrival(captured="bP"))
    assert scoreboard.score("w") == 0


def test_a_custom_observer_only_needs_the_interface():
    # What a broadcaster to remote clients would look like: it receives the
    # event whole and needs nothing else from the engine.
    class Recorder(GameObserver):
        def __init__(self):
            self.seen = []

        def on_event(self, event):
            self.seen.append(event)

    observer = Recorder()
    event = arrival()
    observer.on_event(event)
    assert observer.seen == [event]
