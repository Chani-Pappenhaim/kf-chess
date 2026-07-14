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
from game.board_mapper import BoardMapper
from game.controller import Controller
from graphics.assets import AssetLoader, read_image, solid
from graphics.window import Window
from ui.graphics_renderer import GraphicsRenderer
from ui.hud import Hud
from ui.input_source import InputTranslator

_STRIP_COLOR = (30, 30, 30, 255)  # dark HUD strip below the board


def load_board_background(config=settings):
    """Load board.png resized to the logical board size (a fresh Img each call,
    so callers may draw pieces onto it without corrupting a shared canvas)."""
    return read_image(config.BOARD_IMAGE, size=(config.BOARD_PX, config.BOARD_PX))


def new_base_canvas(config=settings):
    """Full window canvas: the board at the top and a blank HUD strip below."""
    canvas = solid(config.BOARD_PX, config.CANVAS_HEIGHT, _STRIP_COLOR)
    load_board_background(config).draw_on(canvas, 0, 0)
    return canvas


def _compose(config):
    """Build the engine and its board from board.csv (the graphical
    composition root; mirrors main.run's dependency graph)."""
    registry = build_default_registry(config)
    with open(config.BOARD_CSV, encoding="utf-8") as handle:
        board = load_csv_board(handle.read().splitlines(), registry, config)
    arbiter = RealTimeArbiter(
        board=board,
        promotion_rule=LastRankPromotion(config.PAWN_DIRECTION),
        config=config,
    )
    engine = GameEngine(
        board=board,
        rule_engine=RuleEngine(rule_registry=registry, config=config),
        arbiter=arbiter,
        win_condition=KingCaptureWinCondition(),
        config=config,
    )
    return engine, board


def build_engine(config=settings):
    """Compose the GameEngine alone (used where no input handling is needed)."""
    engine, _ = _compose(config)
    return engine


def build_game(config=settings):
    """Compose the engine plus a Controller wired to it, ready to drive input."""
    engine, board = _compose(config)
    controller = Controller(engine, BoardMapper(board, config.CELL_SIZE))
    return engine, controller


def run(config=settings):  # pragma: no cover - real-time GUI loop
    window = Window(config.WINDOW_TITLE)
    engine, controller = build_game(config)
    translator = InputTranslator(controller)
    sprites = AssetLoader(config).load_sprite_library()
    renderer = GraphicsRenderer(sprites, config.CELL_SIZE)
    hud = Hud(config)
    base = new_base_canvas(config)
    previous = time.perf_counter()
    try:
        running = True
        while running:
            now = time.perf_counter()
            engine.wait(int((now - previous) * 1000))
            previous = now
            model = engine.render_model()
            canvas = renderer.render(
                model, base, clock_ms=engine.clock, selected=controller.selected
            )
            hud.draw(canvas, model)
            window.show(canvas)
            for event in window.poll_events():
                if event[0] == "quit":
                    running = False
                else:
                    translator.handle(event)
    finally:
        window.close()


if __name__ == "__main__":  # pragma: no cover
    run()
