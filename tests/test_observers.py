import types

from config import settings
from realtime.real_time_arbiter import ArrivalEvent
from game.models import JumpEvent
from game.move_log import MoveLog
from game.notation import CoordinateNotation
from game.observers import GameObserver, MoveRecorder, CaptureScorer, SoundPlayer
from game.scoreboard import Scoreboard


def arrival(piece="wR", origin=(5, 0), destination=(5, 2), captured=None, at_ms=1000):
    return ArrivalEvent(
        piece=piece,
        origin=origin,
        destination=destination,
        captured=captured,
        at_ms=at_ms,
    )


class FakeAudio:
    def __init__(self):
        self.played = []

    def play(self, path):
        self.played.append(path)


def sound_config(enabled=True):
    return types.SimpleNamespace(
        SOUND_ENABLED=enabled,
        MOVE_SOUND="move", CAPTURE_SOUND="capture",
        JUMP_SOUND="jump", GAME_OVER_SOUND="game_over",
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


def test_move_recorder_ignores_a_jump():
    # A jump is not a move, so it never reaches the log.
    log = MoveLog()
    MoveRecorder(log, CoordinateNotation(8)).on_event(JumpEvent("wN", (5, 5), 1000))
    assert log.entries() == ()


def test_sound_player_picks_a_sound_per_event():
    audio = FakeAudio()
    player = SoundPlayer(audio, sound_config())
    player.on_event(arrival(captured=None))     # move
    player.on_event(arrival(captured="bP"))     # capture
    player.on_event(arrival(captured="bK"))     # king -> game over
    player.on_event(JumpEvent("wN", (5, 5)))    # jump
    assert audio.played == ["move", "capture", "game_over", "jump"]


def test_sound_player_stays_silent_when_disabled():
    audio = FakeAudio()
    SoundPlayer(audio, sound_config(enabled=False)).on_event(arrival())
    assert audio.played == []


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
