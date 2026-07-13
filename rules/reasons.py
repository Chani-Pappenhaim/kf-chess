class Reason:
    """Stable, machine-readable outcome codes for a requested move.

    Defined once and reused by RuleEngine, GameEngine, and Controller so the
    codes are never scattered as bare string literals. They are not printed by
    `print board`; they exist so unit tests and callers can branch on a
    precise cause instead of a bare boolean.

    Lives in its own module (rather than in game/models.py) so the low-level
    `rules` layer can share this vocabulary without importing upward from the
    `game` layer - the dependency only ever flows downward onto this module.
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
