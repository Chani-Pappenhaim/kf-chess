"""The ordered record of completed moves.

Written to as moves settle, read by the view to draw each player's move table.
It stores only facts - color, the already-formatted text, and the time - so it
decides nothing about layout.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MoveRecord:
    color: str      # 'w' or 'b'
    notation: str   # written form of the move, e.g. 'Ng1-f3'
    time_ms: int    # simulated clock when the move completed


class MoveLog:
    def __init__(self):
        self._records = []

    def record(self, color, notation, time_ms):
        self._records.append(MoveRecord(color, notation, time_ms))

    def entries(self, color=None):
        """Recorded moves in order: all of them, or only `color`'s when given."""
        if color is None:
            return tuple(self._records)
        return tuple(r for r in self._records if r.color == color)
