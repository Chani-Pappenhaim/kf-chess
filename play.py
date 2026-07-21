"""KungFu Chess - graphical entry point (real-time UI).

Deliberately separate from main.py, which drives the text command-script. This
one builds the same GameEngine, loads the board from CSV, and runs it inside a
window with sprites and a real-time frame loop.
"""
from __future__ import annotations

from config import settings
from board.loaders import load_csv_board
from game.composition import (
    build_registry,
    build_engine as _build_engine,
    build_game as _build_game,
)
from audio.player import AudioPlayer
from audio.cues import subscribe_sound
from events.bus import EventBus
from graphics.assets import AssetLoader, read_image, solid
from graphics.window import Window
from ui.game_loop import GameLoop
from ui.graphics_renderer import GraphicsRenderer
from ui.hud import Hud
from ui.animation import subscribe_banner
from ui.input_source import InputTranslator

_BACKGROUND_COLOR = (238, 238, 238, 255)  # light window background around the board


def load_board_background(config=settings):
    """The board image at the logical board size. A fresh Img each call, so a
    caller may draw onto it without corrupting a shared canvas."""
    return read_image(config.BOARD_IMAGE, size=(config.BOARD_PX, config.BOARD_PX))


def new_base_canvas(config=settings):
    """The window's unchanging backdrop: the board drawn at its framed origin,
    leaving room for the panels and strips the Hud fills in each frame.

    Built once and copied per frame, since none of it ever changes.
    """
    canvas = solid(config.WINDOW_WIDTH, config.WINDOW_HEIGHT, _BACKGROUND_COLOR)
    load_board_background(config).draw_on(canvas, config.BOARD_ORIGIN_X, config.BOARD_ORIGIN_Y)
    return canvas


def _compose(config):
    """Load the board from CSV. The only place that knows the format; the rest
    of the wiring is delegated to game.composition."""
    registry = build_registry(config)
    with open(config.BOARD_CSV, encoding="utf-8") as handle:
        board = load_csv_board(handle.read().splitlines(), registry, config)
    return board, registry


def build_engine(config=settings, bus=None):
    """Compose the GameEngine alone (used where no input handling is needed)."""
    board, registry = _compose(config)
    return _build_engine(board, registry, config, bus or EventBus())


def build_game(config=settings, bus=None):
    """The engine plus a Controller, ready to take input. The mapper is offset
    by the board's origin so clicks on the framed board hit the right cell."""
    board, registry = _compose(config)
    origin = (config.BOARD_ORIGIN_X, config.BOARD_ORIGIN_Y)
    return _build_game(board, registry, config, bus or EventBus(), board_origin=origin)


def run(config=settings):  # pragma: no cover - real-time GUI loop
    """Build and wire every component, then hand them to the GameLoop."""
    window = Window(config.WINDOW_TITLE)
    bus = EventBus()
    engine, controller = build_game(config, bus)
    subscribe_sound(bus, AudioPlayer(), config)
    translator = InputTranslator(controller)
    sprites = AssetLoader(config).load_sprite_library()
    origin = (config.BOARD_ORIGIN_X, config.BOARD_ORIGIN_Y)
    renderer = GraphicsRenderer(sprites, config.CELL_SIZE, origin=origin)
    hud = Hud(config, subscribe_banner(bus, config))
    base = new_base_canvas(config)
    engine.start()
    GameLoop(window, engine, controller, renderer, hud, translator, base).run()


if __name__ == "__main__":  # pragma: no cover
    run()
