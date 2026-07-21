from config import settings
from game.events import MoveCompleted, PieceCaptured
from game.move_log import MoveLog
from game.notation import CoordinateNotation
from game.scoreboard import Scoreboard
from game.subscribers import MoveRecorder, CaptureScorer


def completed(piece="wR", origin=(5, 0), destination=(5, 2), captured=None, at_ms=1000):
    return MoveCompleted(
        piece=piece,
        origin=origin,
        destination=destination,
        captured=captured,
        at_ms=at_ms,
    )


def test_move_recorder_logs_the_move_in_notation():
    log = MoveLog()
    MoveRecorder(log, CoordinateNotation(8)).record(completed())
    assert log.entries("w")[0].notation == "Ra3-c3"


def test_move_recorder_takes_the_time_from_the_event():
    # The event carries its own timestamp, so the recorder needs no clock.
    log = MoveLog()
    MoveRecorder(log, CoordinateNotation(8)).record(completed(at_ms=4200))
    assert log.entries("w")[0].time_ms == 4200


def test_capture_scorer_awards_the_captured_piece_value():
    scoreboard = Scoreboard(settings.COLORS)
    event = PieceCaptured(captor="wR", captured="bP", cell=(5, 2), at_ms=1000)
    CaptureScorer(scoreboard, settings.PIECE_VALUES).award(event)
    assert scoreboard.score("w") == settings.PIECE_VALUES["P"]
    assert scoreboard.score("b") == 0


def test_capture_scorer_scores_an_unvalued_kind_as_zero():
    scoreboard = Scoreboard(settings.COLORS)
    event = PieceCaptured(captor="wR", captured="bP", cell=(5, 2), at_ms=1000)
    CaptureScorer(scoreboard, {}).award(event)
    assert scoreboard.score("w") == 0
