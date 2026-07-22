"""Central configuration for KungFu Chess.

All game constants live here so game logic never hardcodes magic numbers.
Changing timing, supported colors, or pawn direction only requires
editing this file - no other module should contain literal values like
these.
"""

# Rendering / timing (milliseconds)
CELL_SIZE = 70
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

# Point value of each piece kind, used by the score panel to credit a capture.
# Standard chess material values; the king is 0 because capturing it ends the
# game (the win condition), so it is never scored as material.
PIECE_VALUES = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 0}

# Gameplay policy: may several moves be in flight at the same time?
# True is the real-time KungFu Chess default: there are no turns, so both
# players move at once and a single player may start further moves while an
# earlier one is still travelling. What limits a player is per-piece, not
# global - a piece that is already moving is "busy", and a piece that just
# finished is "resting" (cooldown) - so each piece is gated on its own while
# the board as a whole stays live. Set False to fall back to the strict
# one-move-at-a-time variant, which resolves a contested route in favour of
# whoever started first.
ALLOW_CONCURRENT_MOVES = True

# Cooldown after a completed action (milliseconds). A move settles into
# long_rest, a jump into short_rest; during the cooldown the piece may not act
# (see RealTimeArbiter / Reason.RESTING). The move cooldown is set here to 5s;
# a jump is a lighter action, so its cooldown is deliberately shorter.
LONG_REST_DURATION = 5000   # after a move
SHORT_REST_DURATION = 3000  # after a jump

# Names of the two rest states, shared by the arbiter that emits them, the view
# that veils a resting piece, and the sprite folder for each rest animation.
LONG_REST_STATE = "long_rest"
SHORT_REST_STATE = "short_rest"

# --- Graphical UI (assets, window, real-time loop) -------------------------
# Only the graphics/ and ui/ layers read these; the text command-script path
# (main.run) never touches them.
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_ROOT = os.path.join(_PROJECT_ROOT, "assets")
BOARD_IMAGE = os.path.join(ASSETS_ROOT, "board.png")
PIECES_ROOT = os.path.join(ASSETS_ROOT, "pieces")
BOARD_CSV = os.path.join(ASSETS_ROOT, "board.csv")

WINDOW_TITLE = "KungFu Chess"
FPS = 60

# Sound effects (graphical UI only). A missing file is silently skipped.
SOUNDS_ROOT = os.path.join(ASSETS_ROOT, "sounds")
SOUND_ENABLED = True
MOVE_SOUND = os.path.join(SOUNDS_ROOT, "move.wav")          # a move settled
CAPTURE_SOUND = os.path.join(SOUNDS_ROOT, "capture.wav")    # a move captured
JUMP_SOUND = os.path.join(SOUNDS_ROOT, "jump.wav")          # a piece jumped
GAME_OVER_SOUND = os.path.join(SOUNDS_ROOT, "game_over.wav")  # the king was taken
BOARD_PX = 8 * CELL_SIZE  # board background is rendered at 8 cells * CELL_SIZE

# Full-window layout: the board sits framed by a coordinate gutter (file/rank
# labels) with a move-list panel on each side, a title strip on top, and a score
# strip both above and below the board. The board's on-canvas origin is derived
# from these, and BoardMapper/GraphicsRenderer are offset by it so clicks and
# sprites still land on the right cell. Only the graphical path uses these; the
# text path never offsets the board (BoardMapper defaults to origin 0,0).
COORD_GUTTER = 28   # strip around the board for the a-h / 1-8 labels
PANEL_WIDTH = 250   # each side move-list panel (Black on the left, White right)
TITLE_HEIGHT = 46   # top strip for the "Name:" title
SCORE_HEIGHT = 40   # score strip, one above and one below the board

BOARD_ORIGIN_X = PANEL_WIDTH + COORD_GUTTER
BOARD_ORIGIN_Y = TITLE_HEIGHT + SCORE_HEIGHT + COORD_GUTTER
WINDOW_WIDTH = 2 * (PANEL_WIDTH + COORD_GUTTER) + BOARD_PX
WINDOW_HEIGHT = TITLE_HEIGHT + 2 * SCORE_HEIGHT + 2 * COORD_GUTTER + BOARD_PX

# Name shown in the top title strip as "Name: <PLAYER_NAME>".
PLAYER_NAME = "Player"

# Written form of each color, for anything that names a player.
COLOR_NAMES = {"w": "White", "b": "Black"}

# Banner overlaid on the board when the game opens and when it ends. The start
# banner clears itself after START_BANNER_MS; the end banner has nothing to
# make way for, so it stays.
START_BANNER_TEXT = "GO!"
START_BANNER_MS = 1500
END_BANNER_TEXT = "{winner} WINS"

# --- Networked play --------------------------------------------------------
# Only server/ and client/ read these; the local paths never touch them.
SERVER_HOST = "localhost"
SERVER_PORT = 8765
SERVER_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}"

# How often the server advances the game and sends the state out. The clock
# lives on the server alone, so this is the only place time passes: clients
# draw what they are sent and never advance anything themselves.
SERVER_TICK_MS = 33

# Shown in the client's window until the server sends the first state.
CONNECTING_TEXT = "connecting..."

# What the shell and the server say to a person. Kept here with the rest of the
# user-facing text so wording is changed in one place, not hunted through code.
USERNAME_PROMPT = "username: "
PASSWORD_PROMPT = "password: "
SERVER_STOPPED_MESSAGE = "server stopped"
REJECT_WRONG_PASSWORD = "wrong password"
REJECT_GAME_FULL = "the game already has two players"

# Printed in the shell once the server answers a login, so a player knows whether
# a fresh account was made or a known one was recognised.
ACCOUNT_CREATED_MESSAGE = "account created - welcome, {name}!"
WELCOME_BACK_MESSAGE = "welcome back, {name}!"

# Drawn on the score strip. The rating gets its own label rather than parentheses
# so it reads as the standing it is; the marker tags the strip that is you (kept
# ASCII, as the cv2 text renderer draws no Hebrew).
RATING_LABEL = "Rating"
YOU_MARKER = "  <- you"

# Accounts, saved on the server. Every new player starts at STARTING_RATING and
# moves by ELO after each game; ELO_K_FACTOR is how far a single result can shift
# a rating. Only server-side account handling reads these.
ACCOUNTS_DB = os.path.join(_PROJECT_ROOT, "accounts.db")
STARTING_RATING = 1200
ELO_K_FACTOR = 32
