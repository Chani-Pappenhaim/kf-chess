"""Who is playing which colour.

The server's alone: the game itself is turnless and colour-blind, so player
identity lives out here, beside the connections, and never reaches the engine.

The first to join takes the first colour, the second the next, and a third is
turned away - two players, as the slide asks. Spectators come later, and will be
those this refuses a colour rather than the connection.
"""
from __future__ import annotations


class PlayerRegistry:
    def __init__(self, colors):
        self._colors = tuple(colors)
        self._by_color = {}  # colour -> username

    def join(self, username):
        """Assign the next free colour to `username`, or None when both are taken."""
        for color in self._colors:
            if color not in self._by_color:
                self._by_color[color] = username
                return color
        return None

    def leave(self, color):
        """Free a colour when its player disconnects, so the seat can be retaken."""
        self._by_color.pop(color, None)

    def names(self):
        """A plain {colour: username} for the state the view draws."""
        return dict(self._by_color)
