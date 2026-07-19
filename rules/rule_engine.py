from dataclasses import dataclass

from rules.reasons import Reason
from rules.movement_strategy import MoveContext


@dataclass(frozen=True)
class MoveValidation:
    """A legality verdict: Reason.OK, or the code explaining the refusal."""

    is_valid: bool
    reason: str


@dataclass(frozen=True)
class MovePlan:
    """A validated move, reduced to what is needed to step it."""

    path: tuple                # cells walked, source excluded, destination last
    may_capture_final: bool    # false only for a pawn moving straight


class RuleEngine:
    """Answers whether a move is legal. Read-only, and unaware of time."""

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
        """Whether the piece on `start` may capture an enemy on `end`.

        Re-asks the piece's strategy with an occupied target, so a rule like
        "a pawn cannot capture straight ahead" stays inside the piece.
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
        """Turn a move into a MovePlan. Call only after validate_move accepts it."""
        piece = board.get(*start)
        strategy = self._registry.get(piece[1])
        return MovePlan(
            path=strategy.path(start, end),
            may_capture_final=self.may_capture(board, start, end),
        )

    def legal_targets(self, board, start):
        """Every cell the piece on `start` may move to right now."""
        return tuple(
            (r, c)
            for r in range(board.height)
            for c in range(board.width)
            if self.validate_move(board, start, (r, c)).is_valid
        )
