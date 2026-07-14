"""SpriteAnimation - a frame sequence played on a clock.

Pure and window-free: it holds the frames (Img objects) plus the timing read
from a state's config.json (frames-per-second and whether it loops) and answers
"which frame at time t". Deciding *when* to switch states is not its job - that
belongs to the game state machine - so it also exposes the state to fall into
when a non-looping animation finishes (config's next_state_when_finished).
"""
from __future__ import annotations


class SpriteAnimation:
    def __init__(self, frames, fps, loop, next_state):
        if not frames:
            raise ValueError("a SpriteAnimation needs at least one frame")
        self._frames = tuple(frames)
        self._fps = fps
        self._loop = loop
        self.next_state = next_state

    @property
    def frame_count(self):
        return len(self._frames)

    @property
    def loop(self):
        return self._loop

    def duration_ms(self):
        """Total play time of one pass through the frames."""
        if self._fps <= 0:
            return 0
        return int(1000 * self.frame_count / self._fps)

    def is_finished(self, elapsed_ms):
        """A looping animation never finishes; a one-shot finishes once its
        last frame's time has passed."""
        return not self._loop and elapsed_ms >= self.duration_ms()

    def frame_at(self, elapsed_ms):
        """The frame to show `elapsed_ms` into the animation."""
        if self._fps <= 0:
            return self._frames[0]
        index = int(elapsed_ms * self._fps / 1000)
        if self._loop:
            index %= self.frame_count
        else:
            index = min(index, self.frame_count - 1)
        return self._frames[index]
