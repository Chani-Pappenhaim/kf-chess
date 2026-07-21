"""Sound cues for game events.

Lives here rather than beside the game because sound is presentation: nothing
under game/ knows it exists.
"""
from __future__ import annotations

from game.events import MoveCompleted, PieceCaptured, JumpStarted, GameEnded


class SoundCues:
    """Plays one sound per event, through an injected audio player."""

    def __init__(self, audio, config):
        self._audio = audio
        self._config = config

    def play_move(self, event):
        self._audio.play(self._config.MOVE_SOUND)

    def play_capture(self, event):
        self._audio.play(self._config.CAPTURE_SOUND)

    def play_jump(self, event):
        self._audio.play(self._config.JUMP_SOUND)

    def play_game_over(self, event):
        self._audio.play(self._config.GAME_OVER_SOUND)


def subscribe_sound(bus, audio, config):
    """Wire the cues onto `bus`, or leave it untouched when sound is off.

    Silence is the absence of a subscription rather than a check inside every
    cue, so nothing has to ask whether it is allowed to make a noise.
    """
    if not config.SOUND_ENABLED:
        return
    cues = SoundCues(audio, config)
    bus.subscribe(MoveCompleted, cues.play_move)
    bus.subscribe(PieceCaptured, cues.play_capture)
    bus.subscribe(JumpStarted, cues.play_jump)
    bus.subscribe(GameEnded, cues.play_game_over)
