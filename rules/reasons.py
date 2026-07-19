from enum import Enum


class Reason(str, Enum):
    """Reasons for a move to be rejected."""

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
    RESTING = "resting"
