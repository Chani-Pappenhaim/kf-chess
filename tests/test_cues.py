import types

from audio.cues import subscribe_sound
from events.bus import EventBus
from game.events import MoveCompleted, PieceCaptured, JumpStarted, GameEnded


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


def publish_one_of_each(bus):
    bus.publish(MoveCompleted("wR", (5, 0), (5, 2), None, 1000))
    bus.publish(PieceCaptured("wR", "bP", (5, 2), 1000))
    bus.publish(JumpStarted("wN", (5, 5), 1200))
    bus.publish(GameEnded("w", 1400))


def test_each_event_plays_its_own_sound():
    bus, audio = EventBus(), FakeAudio()
    subscribe_sound(bus, audio, sound_config())
    publish_one_of_each(bus)
    assert audio.played == ["move", "capture", "jump", "game_over"]


def test_sound_off_subscribes_nothing():
    # Silence is the absence of a subscription, not a check inside every cue.
    bus, audio = EventBus(), FakeAudio()
    subscribe_sound(bus, audio, sound_config(enabled=False))
    publish_one_of_each(bus)
    assert audio.played == []
