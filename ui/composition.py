"""The one place the graphical UI is wired.

Both graphical entry points build exactly this: the same window furniture, the
same sprites, the same sound and banners. What differs between playing locally
and playing over a network is only which gateway is handed in - so that is the
only argument, and the two can never drift apart.
"""
from __future__ import annotations

from audio.cues import subscribe_sound
from audio.player import AudioPlayer
from graphics.assets import AssetLoader, read_image, solid
from ui.animation import subscribe_banner
from ui.game_loop import GameLoop
from ui.graphics_renderer import GraphicsRenderer
from ui.hud import Hud
from ui.input_source import InputTranslator

_BACKGROUND_COLOR = (238, 238, 238, 255)  # light window background around the board


def board_origin(config):
    return config.BOARD_ORIGIN_X, config.BOARD_ORIGIN_Y


def load_board_background(config):
    """The board image at the logical board size. A fresh Img each call, so a
    caller may draw onto it without corrupting a shared canvas."""
    return read_image(config.BOARD_IMAGE, size=(config.BOARD_PX, config.BOARD_PX))


def new_base_canvas(config):
    """The window's unchanging backdrop: the board drawn at its framed origin,
    leaving room for the panels and strips the Hud fills in each frame.

    Built once and copied per frame, since none of it ever changes.
    """
    canvas = solid(config.WINDOW_WIDTH, config.WINDOW_HEIGHT, _BACKGROUND_COLOR)
    load_board_background(config).draw_on(canvas, *board_origin(config))
    return canvas


def build_loop(window, gateway, controller, bus, config):
    """Everything drawn around `gateway`, wired into a frame loop.

    The bus is handed in already carrying whatever the game publishes onto it -
    an engine's own bus when playing locally, one fed from the network when not.
    """
    subscribe_sound(bus, AudioPlayer(), config)
    renderer = GraphicsRenderer(
        AssetLoader(config).load_sprite_library(),
        config.CELL_SIZE,
        origin=board_origin(config),
    )
    return GameLoop(
        window=window,
        engine=gateway,
        controller=controller,
        renderer=renderer,
        hud=Hud(config, subscribe_banner(bus, config)),
        translator=InputTranslator(controller),
        base=new_base_canvas(config),
    )
