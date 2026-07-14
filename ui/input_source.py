"""InputTranslator - routes raw Window device events to a Controller.

One instance per input source, so adding a second player later is just a second
(source, controller) pair - the engine and rendering are untouched. Window emits
device events (a mouse button at a pixel, or quit); this maps left-click to the
Controller's select/move and right-click to jump. Quit is not a game command, so
it is ignored here and left for the loop to act on.
"""
from __future__ import annotations


class InputTranslator:
    def __init__(self, controller):
        self._controller = controller

    def handle(self, event):
        kind = event[0]
        if kind == "left":
            self._controller.click(event[1], event[2])
        elif kind == "right":
            self._controller.jump(event[1], event[2])
