"""Sound cues for game events.

Lives here rather than beside the game because sound is presentation: nothing
under game/ knows it exists.
"""
from __future__ import annotations

from game.events import MoveCompleted, PieceCaptured, JumpStarted, GameEnded


def _cue(audio, sound):
    """A subscriber that plays `sound`, whatever the event carries."""
    return lambda event: audio.play(sound)


def subscribe_sound(bus, audio, config):
    """Wire one sound per event onto `bus`, or leave it untouched when sound is off.

    Silence is the absence of a subscription rather than a check before every
    sound, so nothing has to ask whether it is allowed to make a noise.
    """
    if not config.SOUND_ENABLED:
        return
    for event_type, sound in (
        (MoveCompleted, config.MOVE_SOUND),
        (PieceCaptured, config.CAPTURE_SOUND),
        (JumpStarted, config.JUMP_SOUND),
        (GameEnded, config.GAME_OVER_SOUND),
    ):
        bus.subscribe(event_type, _cue(audio, sound))
