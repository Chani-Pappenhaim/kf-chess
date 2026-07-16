from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    """A piece in flight, stepping one cell at a time along a precomputed path.

    Owned by RealTimeArbiter, not Board: the board stores logical occupancy of
    the cell the piece currently sits on, while the *plan* for where it is still
    going lives here until the move terminates.

    The move is advanced FUNCTIONALLY (this is a frozen dataclass): each step
    produces a new Move via ``dataclasses.replace`` with ``index`` bumped and a
    freshly scheduled ``arrival`` - never a mutated field. That keeps every model
    in this layer immutable and makes a half-stepped move safe to share with the
    view.

    Fields:
      - ``piece``    - the token being moved ('wR', ...).
      - ``source``   - the ORIGINAL cell the move started from. Needed for
                       ArrivalEvent.origin (notation "from"), because the board
                       clears the source as the piece steps off it, so it cannot
                       be recovered later.
      - ``path``     - ordered cells the piece steps through, EXCLUDING source and
                       ENDING at the final cell (pure geometry, built by the rules
                       layer). A knight's atomic L-jump is just ``(end,)``.
      - ``index``    - how many cells of ``path`` have been committed; 0 means the
                       piece is still on ``source`` and has not moved yet.
      - ``may_capture_final`` - may this piece capture an enemy sitting on its
                       FINAL cell? (slider/king/queen/knight/pawn-diagonal True,
                       pawn-straight False). Decided by the rules layer; the
                       arbiter only obeys the flag - it never learns piece rules.
      - ``arrival``  - the simulated-clock time at which the piece reaches
                       ``next_cell`` (the pending step).
    """

    piece: str
    source: tuple
    path: tuple
    index: int
    may_capture_final: bool
    arrival: int

    @property
    def current(self):
        """The cell the piece physically sits on right now (== source until it
        has committed its first step, then the last committed path cell)."""
        return self.source if self.index == 0 else self.path[self.index - 1]

    @property
    def next_cell(self):
        """The cell the pending step is heading into (the one ``arrival`` times)."""
        return self.path[self.index]

    @property
    def final(self):
        """The move's destination cell - where it settles if never blocked."""
        return self.path[-1]

    def advanced(self):
        """True once the piece has left ``source`` (committed >= 1 cell). A move
        blocked at its very first step never advanced, and must be dropped with
        no event/cooldown rather than settled."""
        return self.index > 0


@dataclass(frozen=True)
class Jump:
    """A piece that is airborne on a cell until end_time.

    While airborne it can intercept an enemy Move arriving on the same cell.
    """

    piece: str
    cell: tuple
    end_time: int


@dataclass(frozen=True)
class MotionView:
    """A read-only snapshot of the piece's CURRENT sub-step, for the view layer.

    Because motion is now per-cell, ``start`` is the cell the piece currently
    sits on, ``end`` is the NEXT cell it is stepping into (not the far
    destination), and ``progress`` (0..1) is the fraction of that single sub-step
    elapsed at the current clock. The renderer slides start->end within the step;
    the engine keys the motions dict by ``start`` (the piece's current board cell)
    so an in-flight slider is found where it now sits.
    """

    piece: str
    start: tuple
    end: tuple
    progress: float
