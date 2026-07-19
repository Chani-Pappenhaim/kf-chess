from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    """A piece in flight, stepping one cell at a time along its path.

    Frozen: a step produces a new Move via ``dataclasses.replace`` rather than
    mutating one, so a half-stepped move is safe to hand to the view.
    """

    piece: str               # the token being moved, e.g. 'wR'
    source: tuple            # where the move began; the board has since cleared it
    path: tuple              # cells to step through, source excluded, destination last
    index: int               # cells of `path` already committed; 0 = still on source
    may_capture_final: bool  # may it take an enemy on the last cell?
    arrival: int             # clock time at which it reaches `next_cell`

    @property
    def current(self):
        """The cell the piece sits on right now."""
        return self.source if self.index == 0 else self.path[self.index - 1]

    @property
    def next_cell(self):
        """The cell the pending step is heading into, timed by `arrival`."""
        return self.path[self.index]

    @property
    def final(self):
        """Where the move settles if nothing blocks it."""
        return self.path[-1]

    def advanced(self):
        """Whether the piece has left `source`. A move blocked on its very first
        step never did, and is dropped rather than settled."""
        return self.index > 0


@dataclass(frozen=True)
class Jump:
    """A piece airborne on its own cell until `end_time`.

    While airborne it intercepts an enemy move arriving on that cell.
    """

    piece: str
    cell: tuple
    end_time: int


@dataclass(frozen=True)
class MotionView:
    """The piece's current one-cell step, for the view to interpolate.

    Motion is resolved per cell, so this describes the step in progress, not the
    whole move: the renderer slides the piece from `start` to `end` by
    `progress`.
    """

    piece: str
    start: tuple      # the cell it is stepping off
    end: tuple        # the next cell, not the far destination
    progress: float   # 0..1 through this one step
