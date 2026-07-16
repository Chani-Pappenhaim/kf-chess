from dataclasses import dataclass

from rules.reasons import Reason
from rules.movement_strategy import MoveContext


@dataclass(frozen=True)
class MoveValidation:
    """Result of a read-only legality check for a requested move.

    `reason` is always present: ``Reason.OK`` for a legal move, or a stable
    rule-level code otherwise.
    """

    is_valid: bool
    reason: str


@dataclass(frozen=True)
class MovePlan:
    """The rules layer's precomputed recipe for stepping a validated move.

    `path` is the ordered cells the piece walks through (source EXCLUDED, final
    destination INCLUDED — pure geometry from the strategy). `may_capture_final`
    says whether the piece may take an enemy sitting on that final cell (True
    for sliders/king/knight/pawn-diagonal, False for a pawn moving straight).

    Handing the arbiter this frozen plan keeps ALL piece knowledge in the rules
    layer: the arbiter only walks the path and honours the flag, never asking a
    piece anything.
    """

    path: tuple
    may_capture_final: bool


class RuleEngine:
    """Validates whether a move is legal against the current board (Validation
    Service). Read-only: it inspects board state and returns a MoveValidation
    but never mutates the board, starts motion, or knows about game-over.

    Stateless with respect to the board - the board is passed per call - so it
    can be reused and tested in isolation. The piece-rule registry and config
    are injected.
    """

    def __init__(self, rule_registry, config):
        self._registry = rule_registry
        self._config = config

    def validate_move(self, board, start, end):
        if not board.in_bounds(*end):
            return MoveValidation(False, Reason.OUTSIDE_BOARD)
        if board.is_empty(*start):
            return MoveValidation(False, Reason.EMPTY_SOURCE)

        piece = board.get(*start)
        target = board.get(*end)
        if target != self._config.EMPTY_CELL and target[0] == piece[0]:
            return MoveValidation(False, Reason.FRIENDLY_DESTINATION)

        strategy = self._registry.get(piece[1])
        dr, dc = end[0] - start[0], end[1] - start[1]
        context = MoveContext(
            board=board,
            color=piece[0],
            start=start,
            end=end,
            target_occupied=not board.is_empty(*end),
        )
        if not strategy.is_legal(dr, dc, context):
            return MoveValidation(False, Reason.ILLEGAL_PIECE_MOVE)

        return MoveValidation(True, Reason.OK)

    def may_capture(self, board, start, end):
        """Whether the piece on `start` may capture an enemy occupying `end`.

        Reuses the piece's own Strategy: it re-asks `is_legal` with a
        MoveContext whose `target_occupied=True`, so the "can this shape take
        on that square" knowledge stays inside the piece (the arbiter never
        learns rules like "pawns can't capture straight").

        CORRECTNESS CONTRACT: this is only meaningful when called at REQUEST
        time, i.e. for a move whose path is clear. It answers the geometric
        capture question in isolation — a pawn moving straight yields False
        (straight captures are illegal), every other legal shape yields True.
        """
        piece = board.get(*start)
        strategy = self._registry.get(piece[1])
        dr, dc = end[0] - start[0], end[1] - start[1]
        context = MoveContext(
            board=board,
            color=piece[0],
            start=start,
            end=end,
            target_occupied=True,
        )
        return strategy.is_legal(dr, dc, context)

    def build_plan(self, board, start, end):
        """Build the MovePlan for a (presumed validated) move start -> end.

        The single entry point the engine calls to turn a legal request into a
        stepping recipe: it asks the piece's Strategy for its `path` (pure
        geometry) and computes `may_capture_final` via `may_capture`. The
        engine constructs no MoveContext and touches no strategy directly, so
        the coordinator stays dumb and piece knowledge stays here.
        """
        piece = board.get(*start)
        strategy = self._registry.get(piece[1])
        return MovePlan(
            path=strategy.path(start, end),
            may_capture_final=self.may_capture(board, start, end),
        )

    def legal_targets(self, board, start):
        """Every cell the piece on `start` may legally move to right now.

        Runs the same per-square validation as validate_move against the whole
        board, so it inherits all of it: captures are included, friendly-occupied
        and path-blocked squares are excluded, and an empty or off-board source
        yields nothing. Read-only - it never mutates the board.
        """
        return tuple(
            (r, c)
            for r in range(board.height)
            for c in range(board.width)
            if self.validate_move(board, start, (r, c)).is_valid
        )
