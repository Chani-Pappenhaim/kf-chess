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
PANEL_WIDTH = 150   # each side move-list panel; kept narrow so two windows fit side by side
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
# Read from the environment so the same image runs anywhere; the defaults keep
# local runs and the text path unchanged. In a container, KF_SERVER_HOST is set
# to 0.0.0.0 so the server is reachable from outside it.
SERVER_HOST = os.environ.get("KF_SERVER_HOST", "localhost")
SERVER_PORT = int(os.environ.get("KF_SERVER_PORT", "8765"))
SERVER_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}"

# The API Gateway: login over plain HTTP, separate from the game socket.
API_HOST = os.environ.get("KF_API_HOST", "localhost")
API_PORT = int(os.environ.get("KF_API_PORT", "8766"))
API_LOGIN_URL = f"http://{API_HOST}:{API_PORT}/login"

# Where the shared state lives once the server runs as more than one instance:
# presence, the room directory, and the matchmaking queue. Defaults to a local
# Redis; in compose it points at the redis service by name.
REDIS_URL = os.environ.get("KF_REDIS_URL", "redis://localhost:6379")

# This instance's identity, so its room ids stay unique among other instances.
SERVER_ID = os.environ.get("KF_SERVER_ID", "local")

# Accounts store: PostgreSQL when set, else the local SQLite file below.
DATABASE_URL = os.environ.get("KF_DATABASE_URL", "")

# Set to run several Game Servers behind a WebSocket Gateway: the room
# directory and login tokens move to Redis (shared), instead of this one
# process's memory. Off by default, so a single `python -m server` still needs
# nothing but itself.
DISTRIBUTED = os.environ.get("KF_DISTRIBUTED", "") != ""

# The WebSocket Gateway: the public socket a client actually connects to. It
# picks a Game Server for a fresh session, or the one a JoinRoom already names.
GATEWAY_HOST = os.environ.get("KF_GATEWAY_HOST", "localhost")
GATEWAY_PORT = int(os.environ.get("KF_GATEWAY_PORT", "8760"))

# The Game Servers the Gateway routes to: "id=ws://host:port" pairs, comma
# separated, each id matching that server's own SERVER_ID.
GAME_SERVERS = os.environ.get("KF_GAME_SERVERS", "local=ws://localhost:8765")

# How often the server advances the game and sends the state out. The clock
# lives on the server alone, so this is the only place time passes: clients
# draw what they are sent and never advance anything themselves.
SERVER_TICK_MS = 33

MS_PER_SECOND = 1000  # the game counts in milliseconds, asyncio.sleep in seconds

# How many trailing move records a StateUpdate carries. Without a cap this
# field alone would grow every tick for as long as the game runs, dwarfing the
# rest of the message; the move table only ever shows the tail anyway, and
# each move a client already saw arrives once more as its own EventNotice.
STATE_MOVE_HISTORY_LIMIT = 40

# Shown in the client's window until the server sends the first state.
CONNECTING_TEXT = "connecting..."

# What the shell and the server say to a person. Kept here with the rest of the
# user-facing text so wording is changed in one place, not hunted through code.
USERNAME_PROMPT = "username: "
PASSWORD_PROMPT = "password: "
SERVER_STOPPED_MESSAGE = "server stopped"
REJECT_WRONG_PASSWORD = "wrong password"
REJECT_INVALID_TOKEN = "invalid session"
REJECT_GAME_FULL = "the game already has two players"
REJECT_NO_SUCH_ROOM = "no room with that id"

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
ACCOUNTS_DB = os.environ.get("KF_ACCOUNTS_DB", os.path.join(_PROJECT_ROOT, "accounts.db"))
STARTING_RATING = 1200
ELO_K_FACTOR = 32

# Every /login reply (new account, wrong password, or success alike) waits a
# random extra beat in this range before it is sent - defense in depth against
# timing analysis beyond what equal-cost pbkdf2 hashing and constant-time
# comparison already close. Applied uniformly to every outcome: jittering only
# the failure case would itself become a new signal.
LOGIN_JITTER_MIN_MS = 0
LOGIN_JITTER_MAX_MS = 150

# --- Rooms, matchmaking, and disconnect (slides 6-7) -----------------------
# Only server/ and client/ read these. Every duration is measured from the
# injected tick, never wall-clock, so the server clock stays the only clock.

# "Play" quick-match: pair two seekers whose ratings are within this many
# points; give up after MATCHMAKING_TIMEOUT_MS and report that none was found.
MATCHMAKING_ELO_RANGE = 100
MATCHMAKING_TIMEOUT_MS = 60000

# A disconnected player is given this long to matter before the game resigns in
# their name; the remaining player watches the seconds tick down.
DISCONNECT_GRACE_MS = 20000

# How a game ended, carried on GameEnded so the banner can tell a forfeit (a
# player who left) from a win on the board.
GAME_END_FORFEIT = "forfeit"
FORFEIT_BANNER_TEXT = "{winner} WINS - OPPONENT LEFT"

# Home screen (shown after login) and its two buttons.
PLAY_BUTTON_TEXT = "Play"
ROOM_BUTTON_TEXT = "Room"
HOME_BUTTON_WIDTH = 220
HOME_BUTTON_HEIGHT = 72
HOME_BUTTON_GAP = 30                       # vertical space between the two buttons
HOME_BUTTON_COLOR = (210, 210, 210, 255)   # button fill (BGRA)

# Client status lines while finding a game or when something goes wrong.
SEARCHING_TEXT = "searching for an opponent..."
NO_OPPONENT_MESSAGE = "no opponent found - press Play to retry"
SERVER_UNAVAILABLE_TEXT = "server unavailable"
CONNECTION_LOST_TEXT = "connection lost"

# Drawn on the game screen: the room id up top, the disconnect countdown, and
# who is watching.
ROOM_ID_LABEL = "Room {room_id}"
DISCONNECT_NOTICE = "opponent left - resigning in {seconds}"
VIEWERS_LABEL = "Watching: {names}"
SPECTATOR_LABEL = "spectating"  # marks a viewer's own screen, beside the room id

# The Room dialog (native tkinter): title, prompt, and its three buttons.
ROOM_DIALOG_TITLE = "Room"
ROOM_DIALOG_PROMPT = "room id (blank to create)"
ROOM_DIALOG_CREATE = "Create"
ROOM_DIALOG_JOIN = "Join"
ROOM_DIALOG_CANCEL = "Cancel"

# Activity logs, one per side, capturing every line that crosses the wire.
SERVER_LOG_PATH = os.path.join(_PROJECT_ROOT, "server.log")
CLIENT_LOG_PATH = os.path.join(_PROJECT_ROOT, "client.log")
