"""KungFu Chess - graphical entry point (real-time UI).

Separate from main.py on purpose: main.run drives the text command-script
(and the VPL grader) and stays untouched. This entry opens the cv2 window and
runs the real-time loop. For now it only shows the board background; pieces,
input and animation are layered on in later milestones.
"""
from __future__ import annotations

from config import settings
from graphics.assets import read_image
from graphics.window import Window


def load_board_background(config=settings):
    """Load board.png resized to the logical board size (a fresh Img each call,
    so callers may draw pieces onto it without corrupting a shared canvas)."""
    return read_image(config.BOARD_IMAGE, size=(config.BOARD_PX, config.BOARD_PX))


def run(config=settings):  # pragma: no cover - real-time GUI loop
    window = Window(config.WINDOW_TITLE)
    background = load_board_background(config)
    try:
        running = True
        while running:
            window.show(background)
            if any(event[0] == "quit" for event in window.poll_events()):
                running = False
    finally:
        window.close()


if __name__ == "__main__":  # pragma: no cover
    run()
