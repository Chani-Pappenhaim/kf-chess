"""Scoreboard - accumulated capture points per color.

Domain state that, unlike a live piece count, cannot be derived from the board:
captured pieces have already left it. So it is tracked here as captures happen -
the engine awards points when a move settles with a capture, and the view reads
the totals.
"""
from __future__ import annotations


class Scoreboard:
    def __init__(self, colors):
        self._points = {color: 0 for color in colors}

    def award(self, color, points):
        self._points[color] += points

    def score(self, color):
        return self._points[color]

    def as_dict(self):
        """A plain {color: points} copy for the read model / view."""
        return dict(self._points)
