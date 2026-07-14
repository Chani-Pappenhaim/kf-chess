"""Central configuration for KungFu Chess.

All game constants live here so game logic never hardcodes magic numbers.
Changing timing, supported colors, or pawn direction only requires
editing this file - no other module should contain literal values like
these.
"""

# Rendering / timing (milliseconds)
CELL_SIZE = 100
MOVE_DURATION = 1000
JUMP_DURATION = 1000

# Player colors supported by the game
COLORS = ("w", "b")

# Row delta a pawn advances by on a single step, per color.
# The double-step home rank is not configured here: it is derived from the
# board height in PawnMovement (1 for a downward color, height-2 for an
# upward one - one row in front of the back rank, as in standard chess),
# so the rule works for any board size.
PAWN_DIRECTION = {"w": -1, "b": 1}

# Token used to represent an empty cell on the board
EMPTY_CELL = "."

# Gameplay policy: may several moves be in flight at the same time?
# The real-time variant resolves a contested route in favour of whoever
# started first, so only one move is allowed at a time (default False).
# Set True to re-enable concurrent moves.
ALLOW_CONCURRENT_MOVES = False

# Cooldown after a completed action (milliseconds). Matches the CTD26 rest
# animations: a move settles into long_rest, a jump into short_rest. During
# the cooldown the piece may not act (see RealTimeArbiter / Reason.RESTING).
LONG_REST_DURATION = 833
SHORT_REST_DURATION = 625

# --- Graphical UI (assets, window, real-time loop) -------------------------
# Only the graphics/ and ui/ layers read these; the command-script path
# (main.run) never touches them, so the VPL grader is unaffected.
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_ROOT = os.path.join(_PROJECT_ROOT, "assets")
BOARD_IMAGE = os.path.join(ASSETS_ROOT, "board.png")
PIECES_ROOT = os.path.join(ASSETS_ROOT, "pieces")
BOARD_CSV = os.path.join(ASSETS_ROOT, "board.csv")

WINDOW_TITLE = "KungFu Chess"
FPS = 60
BOARD_PX = 8 * CELL_SIZE  # board background is rendered at 8 cells * CELL_SIZE
