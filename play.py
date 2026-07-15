"""KungFu Chess - graphical entry point (real-time UI).

Separate from main.py on purpose: main.run drives the text command-script (and
the VPL grader) and stays untouched. This entry builds the same GameEngine, but
loads the board from board.csv, renders it graphically through Img, and runs the
real-time loop. Input and richer animation are layered on in later milestones.
"""
from __future__ import annotations

from config import settings
from board.loaders import load_csv_board
from game.composition import (
    build_registry,
    build_engine as _build_engine,
    build_game as _build_game,
)
from graphics.assets import AssetLoader, read_image, solid
from graphics.window import Window
from ui.game_loop import GameLoop
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
    """Load the board from board.csv with a shared registry (the CSV-specific
    part of the graphical composition root). Wiring the rest of the dependency
    graph is delegated to game.composition, so this stays the only place that
    knows the board comes from board.csv."""
    registry = build_registry(config)
    with open(config.BOARD_CSV, encoding="utf-8") as handle:
        board = load_csv_board(handle.read().splitlines(), registry, config)
    return board, registry


def build_engine(config=settings):
    """Compose the GameEngine alone (used where no input handling is needed)."""
    board, registry = _compose(config)
    return _build_engine(board, registry, config)


def build_game(config=settings):
    """Compose the engine plus a Controller wired to it, ready to drive input."""
    board, registry = _compose(config)
    return _build_game(board, registry, config)


def run(config=settings):  # pragma: no cover - real-time GUI loop
    """Composition root: build and wire every component, then hand them to a
    GameLoop that owns the real-time frame loop."""
    window = Window(config.WINDOW_TITLE)
    engine, controller = build_game(config)
    translator = InputTranslator(controller)
    sprites = AssetLoader(config).load_sprite_library()
    renderer = GraphicsRenderer(sprites, config.CELL_SIZE)
    hud = Hud(config)
    base = new_base_canvas(config)
    GameLoop(window, engine, controller, renderer, hud, translator, base).run()


if __name__ == "__main__":  # pragma: no cover
    run()
