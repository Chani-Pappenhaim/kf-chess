"""KungFu Chess - graphical entry point, played locally.

Deliberately separate from main.py, which drives the text command-script. This
one builds the same GameEngine, loads the board from CSV, and runs it inside a
window with sprites and a real-time frame loop.

The window itself is wired by ui.composition, which the networked client uses
too: the only difference between them is which gateway the loop is given.
"""
from __future__ import annotations

from config import settings
from board.loaders import load_csv_board
from events.bus import EventBus
from game.composition import (
    build_registry,
    build_engine as _build_engine,
    build_game as _build_game,
)
from graphics.window import Window
from ui.composition import board_origin, build_loop


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
    return _build_game(
        board, registry, config, bus or EventBus(), board_origin=board_origin(config)
    )


def run(config=settings):  # pragma: no cover - real-time GUI loop
    """Build and wire every component, then hand them to the GameLoop."""
    window = Window(config.WINDOW_TITLE)
    bus = EventBus()
    engine, controller = build_game(config, bus)
    engine.start()
    build_loop(window, engine, controller, bus, config, advance=engine.wait).run()


if __name__ == "__main__":  # pragma: no cover
    run()
