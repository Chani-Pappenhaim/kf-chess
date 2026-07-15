"""KungFu Chess - entry point.

Repository: https://github.com/Chani-Pappenhaim/kf-chess
"""
from __future__ import annotations

import sys

from config import settings
from game.composition import build_registry, build_game
from game.parser import parse_input
from board.loaders import load_text_board, BoardParseError
from view.renderer import BoardRenderer


def run(input_lines, config=settings):
    """Parse input and execute all commands. `config` is injectable so
    tests (or custom variants) can supply alternate settings without
    monkeypatching the settings module.
    """
    board_lines, commands = parse_input(input_lines)
    registry = build_registry(config)

    try:
        board = load_text_board(board_lines, registry, config)
    except BoardParseError as error:
        print("ERROR", error)
        return

    engine, controller = build_game(board, registry, config)
    renderer = BoardRenderer()

    for command in commands:
        _dispatch(command, engine, controller, renderer)


def _dispatch(command, engine, controller, renderer):
    parts = command.split()
    if not parts:
        return

    action = parts[0]
    if action == "click":
        controller.click(int(parts[1]), int(parts[2]))
    elif action == "jump":
        controller.jump(int(parts[1]), int(parts[2]))
    elif action == "wait":
        engine.wait(int(parts[1]))
    elif action == "print":
        print(engine.render(renderer))


def main(input_stream=None):
    """Read a script and run it. `input_stream` is injectable so tests can
    supply a file-like object instead of monkeypatching sys.stdin; it defaults
    to real stdin.
    """
    stream = sys.stdin if input_stream is None else input_stream
    lines = [line.strip() for line in stream]
    run(lines)


if __name__ == "__main__":  # pragma: no cover
    main()
