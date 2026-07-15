"""GameLoop - runs the real-time frame loop, and nothing else.

Its single responsibility is driving one frame after another: advance the game
by the elapsed wall-clock time, render the read model and HUD onto the base
canvas, present the result, and route the window's input to the translator -
until a quit event stops it. It builds nothing; every collaborator (window,
engine gateway, controller, renderer, hud, translator, base canvas) is injected
by the composition root in play.py, so this class touches neither cv2 nor any
engine internals - only the gateway surface (wait, render_model) and the view
components it was handed.

The per-frame work lives in tick(dt), kept pure enough to unit-test with fakes;
run() owns only the wall-clock timing and the window's try/finally lifetime.
"""
from __future__ import annotations

import time


class GameLoop:
    def __init__(self, window, engine, controller, renderer, hud, translator, base):
        self._window = window
        self._engine = engine
        self._controller = controller
        self._renderer = renderer
        self._hud = hud
        self._translator = translator
        self._base = base

    def tick(self, dt):
        """Run one frame: advance the game by `dt` ms, render + present it, and
        route input. Returns False when a quit event was seen (the loop should
        stop), True otherwise."""
        self._engine.wait(dt)
        model = self._engine.render_model()
        canvas = self._renderer.render(
            model, self._base, clock_ms=model.clock,
            selected=self._controller.selected, targets=self._controller.legal_targets,
        )
        self._hud.draw(canvas, model)
        self._window.show(canvas)
        running = True
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
