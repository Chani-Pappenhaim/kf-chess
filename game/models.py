from dataclasses import dataclass


class Reason:
    """Stable, machine-readable outcome codes for a requested move.

    Defined once and reused by RuleEngine, GameEngine, and Controller so the
    codes are never scattered as bare string literals. They are not printed by
    `print board`; they exist so unit tests and callers can branch on a
    precise cause instead of a bare boolean.
    """

    OK = "ok"

    # Rule-level (owned by RuleEngine).
    OUTSIDE_BOARD = "outside_board"
    EMPTY_SOURCE = "empty_source"
    FRIENDLY_DESTINATION = "friendly_destination"
    ILLEGAL_PIECE_MOVE = "illegal_piece_move"

    # Application-level (owned by GameEngine).
    GAME_OVER = "game_over"
    BUSY_SOURCE = "busy_source"
    MOTION_IN_PROGRESS = "motion_in_progress"
    BUSY_CELL = "busy_cell"
    EMPTY_CELL = "empty_cell"


@dataclass(frozen=True)
class MoveResult:
    """The engine's answer at the public command boundary.

    For an accepted command `reason` is ``Reason.OK``; otherwise it carries a
    stable rejection code (either copied from RuleEngine's MoveValidation or an
    application-level reason such as ``game_over``/``motion_in_progress``).
    """

    is_accepted: bool
    reason: str
