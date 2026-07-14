"""KungFu Chess - graphical entry point (real-time UI).

Separate from main.py on purpose: main.run drives the text command-script (and
the VPL grader) and stays untouched. This entry builds the same GameEngine, but
loads the board from board.csv, renders it graphically through Img, and runs the
real-time loop. Input and richer animation are layered on in later milestones.
"""
from __future__ import annotations

import time

from config import settings
from board.loaders import load_csv_board
from realtime.real_time_arbiter import RealTimeArbiter
from rules.rule_registry import build_default_registry
from rules.rule_engine import RuleEngine
from rules.game_conditions import KingCaptureWinCondition, LastRankPromotion
from game.engine import GameEngine
from graphics.assets import AssetLoader, read_image
from graphics.window import Window
from ui.graphics_renderer import GraphicsRenderer


def load_board_background(config=settings):
    """Load board.png resized to the logical board size (a fresh Img each call,
    so callers may draw pieces onto it without corrupting a shared canvas)."""
    return read_image(config.BOARD_IMAGE, size=(config.BOARD_PX, config.BOARD_PX))


def build_engine(config=settings):
    """Compose the full GameEngine with the board loaded from board.csv.

    Mirrors main.run's dependency graph; kept here so the graphical entry owns
    its own composition root without disturbing the command-script one.
    """
    registry = build_default_registry(config)
    with open(config.BOARD_CSV, encoding="utf-8") as handle:
        board = load_csv_board(handle.read().splitlines(), registry, config)
    arbiter = RealTimeArbiter(
        board=board,
        promotion_rule=LastRankPromotion(config.PAWN_DIRECTION),
        config=config,
    )
    return GameEngine(
        board=board,
        rule_engine=RuleEngine(rule_registry=registry, config=config),
        arbiter=arbiter,
        win_condition=KingCaptureWinCondition(),
        config=config,
    )


def run(config=settings):  # pragma: no cover - real-time GUI loop
    window = Window(config.WINDOW_TITLE)
    engine = build_engine(config)
    sprites = AssetLoader(config).load_sprite_library()
    renderer = GraphicsRenderer(sprites, config.CELL_SIZE)
    background = load_board_background(config)
    previous = time.perf_counter()
    try:
        running = True
        while running:
            now = time.perf_counter()
            engine.wait(int((now - previous) * 1000))
            previous = now
            canvas = renderer.render(engine.render_model(), background, clock_ms=engine.clock)
            window.show(canvas)
            if any(event[0] == "quit" for event in window.poll_events()):
                running = False
    finally:
        window.close()


if __name__ == "__main__":  # pragma: no cover
    run()
