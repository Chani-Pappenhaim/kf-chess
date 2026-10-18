"""The computer in its seat: a ComputerPlayer per room, ticked with the room.

Each tick runs on the game loop. Every BOT_MOVE_INTERVAL_MS it captures a
Position and submits the strategy's choice to a worker thread; on a later tick,
once the answer is ready, it plays it - re-checked first, since the game kept
moving while the strategy thought. The engine is read and driven only here, on
the loop thread, so the worker never touches live state and nothing needs a
lock.
"""
from __future__ import annotations

import logging

from bot.position import capture

_log = logging.getLogger("kfchess.bot")


class ComputerPlayer:
    def __init__(self, engine, color, strategy, executor, config, report=_log.warning):
        self._engine = engine
        self._color = color
        self._strategy = strategy
        self._executor = executor
        self._config = config
        self._report = report
        self._waited = 0        # ms since the last move was played (or the game began)
        self._pending = None    # a Future of the move being thought about

    @property
    def color(self):
        return self._color

    def tick(self, dt):
        """Play a move whose thinking has finished, or start thinking about
        the next one once the interval has passed. Never blocks."""
        if self._engine.game_over:
            return
        if self._pending is not None:
            if not self._pending.done():
                return
            future, self._pending = self._pending, None
            self._play(future)
            return
        self._waited += dt
        if self._waited < self._config.BOT_MOVE_INTERVAL_MS:
            return
        self._waited = 0
        position = capture(self._engine, self._color)
        if position.moves:
            self._pending = self._executor.submit(self._strategy.choose, position)

    def _play(self, future):
        try:
            move = future.result()
        # A broken strategy must cost this one move, never the game loop that
        # every other room on this server shares.
        except Exception as error:
            self._report(f"computer ({self._color}) could not choose a move: {error!r}")
            return
        if move is None:
            return
        start, end = move
        piece = self._engine.render_model().piece_at(start)
        # The square may have changed hands while the strategy thought; the
        # engine checks everything else (busy, resting, the rules) itself.
        if piece is None or piece.token[0] != self._color:
            return
        self._engine.request_move(start, end)
