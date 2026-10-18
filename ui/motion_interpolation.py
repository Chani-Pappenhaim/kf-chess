"""Turns MoveStepStarted/JumpStarted events into a smooth per-frame progress
GraphicsRenderer can query, instead of only whatever progress fraction the
last StateUpdate happened to carry - the event-driven tier described in
Server_Design.md's network-traffic section, now that StateUpdate itself is
throttled (server/room.py) and no longer arrives every tick.

No clock synchronization with the server is needed: `duration_ms` is a fixed
span independent of when the server's own clock said the step began, so a
step is timed from the moment THIS process actually received the event (its
own clock) - network latency between "the server started the step" and "the
client heard about it" simply makes the local animation start a few
milliseconds later, rather than needing to be measured and corrected for.

Subscribes on the same bus audio/cues.py and ui/animation.py already do, so
it works identically for local play (the engine's own in-process bus) and a
networked client (client/router.py republishes decoded events onto its own
bus) - the same "same events, same bus, no idea it's remote" shape as
everything else in ui/composition.py.
"""
from __future__ import annotations

import time

from game.events import JumpStarted, MoveStepStarted


class MotionInterpolator:
    def __init__(self, bus, clock=time.monotonic):
        self._clock = clock
        self._motions = {}  # cell -> _Motion, keyed the same way the engine
                             # itself keys active motions (by current cell,
                             # not by piece token - several pieces share a
                             # token, e.g. every white pawn is "wP")
        bus.subscribe(MoveStepStarted, self._on_started)
        bus.subscribe(JumpStarted, self._on_started)

    def progress(self, cell, default):
        """This cell's locally-computed progress through its current motion,
        or `default` (the server's last-sent progress) when nothing local is
        tracked for it yet - true right after joining, before this process
        has seen a MoveStepStarted/JumpStarted of its own."""
        motion = self._motions.get(cell)
        if motion is None:
            return default
        if motion.duration_ms <= 0:
            return 1.0
        elapsed_ms = (self._clock() - motion.received_at) * 1000
        return max(0.0, min(1.0, elapsed_ms / motion.duration_ms))

    def _on_started(self, event):
        # MoveStepStarted keys by `start` (the cell it steps off); JumpStarted
        # keys by `cell` (the one cell it never leaves while airborne) - both
        # name the field the render model's own `piece.cell` will match.
        cell = event.start if isinstance(event, MoveStepStarted) else event.cell
        self._motions[cell] = _Motion(self._clock(), event.duration_ms)


class _Motion:
    __slots__ = ("received_at", "duration_ms")

    def __init__(self, received_at, duration_ms):
        self.received_at = received_at
        self.duration_ms = duration_ms
