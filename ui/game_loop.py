"""GameLoop - runs the real-time frame loop, and nothing else.

Its single responsibility is driving one frame after another: advance the local
clock, render the read model and HUD onto the base canvas, present the result,
and route the window's input to the translator - until a quit event stops it. It
builds nothing; every collaborator (window, engine gateway, controller, renderer,
hud, translator, base canvas) is injected by the composition root, so this class
touches neither cv2 nor any engine internals - only the gateway surface
(render_model) and the view components it was handed.

Advancing the clock is a local-only step, so it is injected (`advance`) rather
than sat on the gateway for a networked client to leave empty.

The per-frame work lives in tick(dt), kept pure enough to unit-test with fakes;
run() owns only the wall-clock timing and the window's try/finally lifetime.
"""
from __future__ import annotations

import time


class GameLoop:
    def __init__(self, window, engine, controller, renderer, hud, translator, base,
                 advance=None, alive=None):
        self._window = window
        self._engine = engine
        self._controller = controller
        self._renderer = renderer
        self._hud = hud
        self._translator = translator
        self._base = base
        self._advance = advance  # local clock step; None when the server owns it
        # A predicate the loop checks each frame: False stops it. A networked
        # client passes "is the connection still up"; local play leaves it None
        # and the loop runs until a quit event.
        self._alive = alive or (lambda: True)

    def tick(self, dt):
        """Run one frame: advance the local clock by `dt` ms if there is one,
        render + present it, and route input. Returns False when a quit event was
        seen or the loop's `alive` predicate failed (it should stop), else True."""
        if self._advance is not None:
            self._advance(dt)
        model = self._engine.render_model()
        canvas = self._renderer.render(
            model, self._base, clock_ms=model.clock,
            selected=self._controller.selected, targets=self._controller.legal_targets,
        )
        self._hud.draw(canvas, model)
        self._window.show(canvas)
        running = self._alive()
        for event in self._window.poll_events():
            if event[0] == "quit":
                running = False
            else:
                self._translator.handle(event)
        return running

    def run(self):  # pragma: no cover - real-time GUI loop
        previous = time.perf_counter()
        try:
            running = True
            while running:
                now = time.perf_counter()
                dt = int((now - previous) * 1000)
                previous = now
                running = self.tick(dt)
        finally:
            self._window.close()
