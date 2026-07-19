"""RealTimeArbiter tests - run against a bare FakeBoard with NO rules layer.

The arbiter is a pure stepping mechanism: it walks a precomputed ``path`` (which
these tests hand-build) and obeys a single ``may_capture_final`` flag. Nothing
here imports rules/, and the board is a minimal fake exposing only the surface
the arbiter touches (get/set/is_empty/relocate/height/width) - so if any test
passes, it proves the arbiter needs nothing from the rules layer.
"""

import types

from config import settings
from realtime.real_time_arbiter import RealTimeArbiter

MD = settings.MOVE_DURATION
LR = settings.LONG_REST_DURATION
JD = settings.JUMP_DURATION
EMPTY = settings.EMPTY_CELL


class FakeBoard:
    """The whole board surface the arbiter uses - and nothing more. No legality,
    no rules, no snapshot: proof the arbiter is decoupled from everything above
    the board."""

    def __init__(self, rows):
        self._cells = [list(row) for row in rows]
        self.height = len(self._cells)
        self.width = len(self._cells[0]) if self._cells else 0

    def get(self, row, col):
        return self._cells[row][col]

    def set(self, row, col, value):
        self._cells[row][col] = value

    def is_empty(self, row, col):
        return self._cells[row][col] == EMPTY

    def relocate(self, src, dst):
        (sr, sc), (dr, dc) = src, dst
        self._cells[dr][dc] = self._cells[sr][sc]
        self._cells[sr][sc] = EMPTY


class NoPromotion:
    def promote(self, piece, row, board_height):
        return piece


class PromoteOnTopRank:
    """Pure, row-keyed stand-in for the real promotion rule: a pawn that settles
    on row 0 becomes a queen, and nothing else changes. No rules import."""

    def promote(self, piece, row, board_height):
        if piece[1] == "P" and row == 0:
            return piece[0] + "Q"
        return piece


def make_arbiter(rows, promotion_rule=None):
    board = FakeBoard(rows)
    arbiter = RealTimeArbiter(
        board=board,
        promotion_rule=promotion_rule or NoPromotion(),
        config=settings,
    )
    return arbiter, board


# --- clock / cooldown / jump infrastructure (unchanged behaviour) -----------

def test_active_motions_is_empty_when_nothing_moves():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    assert arbiter.active_motions() == []


def test_clock_advances_with_time():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    assert arbiter.clock == 0
    arbiter.advance_time(250)
    assert arbiter.clock == 250


def test_completed_move_leaves_a_long_rest_cooldown():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), ((0, 1),), True)
    arbiter.advance_time(MD)  # arrives at (0, 1)
    assert arbiter.cooldown_of((0, 1)) == "long_rest"
    assert arbiter.is_resting((0, 1))


def test_cooldown_clears_after_its_duration():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), ((0, 1),), True)
    arbiter.advance_time(MD)
    arbiter.advance_time(LR)  # rest elapses
    assert arbiter.cooldown_of((0, 1)) is None
    assert not arbiter.is_resting((0, 1))


def test_cooldown_progress_rises_from_zero_to_one_across_the_rest():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), ((0, 1),), True)
    arbiter.advance_time(MD)  # arrives, long rest begins
    assert arbiter.cooldown_progress((0, 1)) == 0.0

    arbiter.advance_time(LR // 2)
    assert 0.4 < arbiter.cooldown_progress((0, 1)) < 0.6

    arbiter.advance_time(LR)
    assert arbiter.cooldown_progress((0, 1)) is None


def test_cooldown_progress_is_none_when_not_resting():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    assert arbiter.cooldown_progress((0, 0)) is None


def test_jump_stays_airborne_before_its_duration():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_jump("wR", (0, 0))
    arbiter.advance_time(JD - 1)
    assert arbiter.is_jumping_on((0, 0))
    assert arbiter.cooldown_of((0, 0)) is None


def test_completed_jump_leaves_a_short_rest_cooldown():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_jump("wR", (0, 0))
    arbiter.advance_time(JD)
    assert arbiter.cooldown_of((0, 0)) == "short_rest"


def test_jump_progress_rises_from_zero_towards_one_mid_hop():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_jump("wR", (0, 0))
    assert arbiter.jump_progress((0, 0)) == 0.0
    arbiter.advance_time(JD // 2)
    assert 0.4 < arbiter.jump_progress((0, 0)) < 0.6


def test_jump_progress_is_none_when_not_airborne():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    assert arbiter.jump_progress((0, 0)) is None


def test_jump_progress_is_one_immediately_when_jump_is_instant():
    """Guard for a zero-length JUMP_DURATION config: an airborne piece reads as
    fully landed (1.0) instead of dividing by zero. A jump can be observed at
    take-off (start_jump, then render, before any advance), so unlike a cooldown
    this degenerate-duration branch is reachable and is exercised here."""
    instant = types.SimpleNamespace(
        **{name: getattr(settings, name) for name in dir(settings) if name.isupper()}
    )
    instant.JUMP_DURATION = 0
    arbiter = RealTimeArbiter(FakeBoard([["wR", ".", "."]]), NoPromotion(), instant)
    arbiter.start_jump("wR", (0, 0))
    assert arbiter.jump_progress((0, 0)) == 1.0


# --- single-cell timing (a step has not arrived before its duration) --------

def test_one_step_has_not_arrived_before_duration():
    arbiter, board = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), ((0, 1),), True)
    arbiter.advance_time(MD - 1)
    assert board.get(0, 0) == "wR"  # still at source
    assert board.is_empty(0, 1)
    assert arbiter.has_active_motion() is True


def test_partial_waits_accumulate_within_a_step():
    arbiter, board = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), ((0, 1),), True)
    arbiter.advance_time(MD // 2)
    arbiter.advance_time(MD - MD // 2)
    assert board.get(0, 1) == "wR"


# --- Layer C: per-cell commit ------------------------------------------------

def test_slider_commits_one_cell_per_step():
    """A rook stepping three cells is physically on each intermediate cell in
    turn - one commit per MOVE_DURATION - not teleported at the end."""
    arbiter, board = make_arbiter([["wR", ".", ".", "."]])
    arbiter.start_move("wR", (0, 0), ((0, 1), (0, 2), (0, 3)), True)

    arbiter.advance_time(MD)
    assert board.is_empty(0, 0) and board.get(0, 1) == "wR"

    arbiter.advance_time(MD)
    assert board.is_empty(0, 1) and board.get(0, 2) == "wR"

    events = arbiter.advance_time(MD)
    assert board.is_empty(0, 2) and board.get(0, 3) == "wR"
    assert len(events) == 1
    assert (events[0].origin, events[0].destination) == ((0, 0), (0, 3))
    assert events[0].captured is None


# --- Layer C: pawn G7->G5 stops on G6, source NOT snapped back ---------------

def test_pawn_double_step_stops_short_and_does_not_snap_back():
    """The historic bug: a pawn's double-step blocked at its destination used to
    snap all the way back to its source. Now it stops on the cell it reached and
    logs from source to that cell."""
    # column: row3 pawn -> row2 (mid) -> row1 (dest, blocked by a friendly Q).
    board_rows = [["."], ["wQ"], ["."], ["wP"]]
    arbiter, board = make_arbiter(board_rows)
    arbiter.start_move("wP", (3, 0), ((2, 0), (1, 0)), False)

    arbiter.advance_time(MD)  # steps to the mid cell
    assert board.get(2, 0) == "wP" and board.is_empty(3, 0)

    events = arbiter.advance_time(MD)  # G6->G5 blocked by friendly -> stop
    assert board.get(2, 0) == "wP"     # stayed on the cell it reached
    assert board.is_empty(3, 0)        # NOT snapped back to source
    assert board.get(1, 0) == "wQ"     # friendly untouched
    assert arbiter.cooldown_of((2, 0)) == "long_rest"
    assert len(events) == 1
    assert (events[0].origin, events[0].destination) == ((3, 0), (2, 0))
    assert events[0].captured is None


# --- Layer C: pawn cannot capture straight -> blocks, no capture ------------

def test_pawn_straight_into_enemy_blocks_without_capturing():
    board_rows = [["."], ["bP"], ["."], ["wP"]]
    arbiter, board = make_arbiter(board_rows)
    # Pawn straight: may_capture_final is False.
    arbiter.start_move("wP", (3, 0), ((2, 0), (1, 0)), False)

    arbiter.advance_time(MD)   # -> mid cell
    events = arbiter.advance_time(MD)  # final enemy, may_capture_final False
    assert board.get(2, 0) == "wP"   # stopped short
    assert board.get(1, 0) == "bP"   # enemy NOT captured
    assert events[0].captured is None
    assert events[0].destination == (2, 0)


# --- Layer C: blocked at the very first step -> no trace ---------------------

def test_blocked_at_first_step_leaves_no_event_and_no_cooldown():
    arbiter, board = make_arbiter([["wR", "wP", "."]])
    arbiter.start_move("wR", (0, 0), ((0, 1), (0, 2)), True)
    events = arbiter.advance_time(2 * MD)

    assert events == []                 # never advanced -> no event
    assert board.get(0, 0) == "wR"      # stays on source
    assert board.get(0, 1) == "wP"      # board unchanged
    assert board.is_empty(0, 2)
    assert arbiter.has_active_motion() is False
    assert arbiter.cooldown_of((0, 0)) is None   # no cooldown at all
    assert arbiter.cooldown_of((0, 1)) is None


def test_uncapturable_enemy_at_first_step_leaves_no_trace():
    """Sibling of the same-colour case: a pawn stepping straight onto an
    ADJACENT enemy it may not capture is blocked on its very first step, so it
    never advances - no event, no cooldown, and the enemy is untouched."""
    arbiter, board = make_arbiter([["bP"], ["wP"]])
    # Single-cell straight step (final == first cell); pawns can't capture ahead.
    arbiter.start_move("wP", (1, 0), ((0, 0),), False)
    events = arbiter.advance_time(MD)

    assert events == []                 # never advanced -> no event
    assert board.get(1, 0) == "wP"      # stays on source
    assert board.get(0, 0) == "bP"      # enemy NOT captured
    assert arbiter.has_active_motion() is False
    assert arbiter.cooldown_of((1, 0)) is None   # no cooldown at all


# --- Layer C: capture at the final cell -------------------------------------

def test_capture_at_final_cell():
    arbiter, board = make_arbiter([["wR", ".", "bK"]])
    arbiter.start_move("wR", (0, 0), ((0, 1), (0, 2)), True)
    events = arbiter.advance_time(2 * MD)

    assert board.get(0, 2) == "wR"
    assert board.is_empty(0, 0)
    assert events[0].captured == "bK"
    assert (events[0].origin, events[0].destination) == ((0, 0), (0, 2))


# --- Layer C: cross-traffic (isolation + contention) ------------------------

def test_crossing_move_alone_completes_unobstructed():
    """A single queen crossing an empty file settles normally - the isolation
    baseline for the contention test below."""
    board_rows = [
        [".", ".", "."],
        ["wQ", ".", "."],
        [".", ".", "."],
    ]
    arbiter, board = make_arbiter(board_rows)
    arbiter.start_move("wQ", (1, 0), ((1, 1), (1, 2)), True)
    arbiter.advance_time(MD)
    assert board.get(1, 1) == "wQ"
    events = arbiter.advance_time(MD)
    assert board.get(1, 2) == "wQ"
    assert events[0].destination == (1, 2)


def test_cross_traffic_first_started_claims_the_contested_cell():
    """Rook (up column 1) and Queen (across row 1) both want cell (1,1) at the
    same tick. Insertion order breaks the tie: whoever started first claims it,
    the other sees it occupied and stops."""
    def fresh():
        return make_arbiter([
            [".", ".", "."],
            ["wQ", ".", "."],
            [".", "wR", "."],
        ])

    # Rook started first -> Rook claims (1,1); Queen is blocked at its first step.
    arbiter, board = fresh()
    arbiter.start_move("wR", (2, 1), ((1, 1), (0, 1)), True)  # started first
    arbiter.start_move("wQ", (1, 0), ((1, 1), (1, 2)), True)
    arbiter.advance_time(MD)
    assert board.get(1, 1) == "wR"      # rook won the cell
    assert board.get(1, 0) == "wQ"      # queen never advanced (dropped)
    assert board.is_empty(2, 1)

    # Reverse the insertion order -> Queen claims (1,1) instead. Deterministic.
    arbiter, board = fresh()
    arbiter.start_move("wQ", (1, 0), ((1, 1), (1, 2)), True)  # started first
    arbiter.start_move("wR", (2, 1), ((1, 1), (0, 1)), True)
    arbiter.advance_time(MD)
    assert board.get(1, 1) == "wQ"      # queen won the cell
    assert board.get(2, 1) == "wR"      # rook never advanced (dropped)
    assert board.is_empty(1, 0)


# --- Layer C: knight is atomic and costs 2x MOVE_DURATION -------------------

def test_knight_is_atomic_and_takes_twice_move_duration():
    board_rows = [
        [".", ".", "."],
        [".", ".", "."],
        ["wN", ".", "."],
    ]
    arbiter, board = make_arbiter(board_rows)
    # A knight's plan is a single (end,) L-jump; Chebyshev distance 2 -> 2x cost.
    arbiter.start_move("wN", (2, 0), ((0, 1),), True)

    arbiter.advance_time(MD)  # half of the 2x cost: still airborne on source
    assert board.get(2, 0) == "wN"
    assert board.is_empty(0, 1)
    assert arbiter.has_active_motion() is True

    events = arbiter.advance_time(MD)  # 2 * MD total -> lands atomically
    assert board.get(0, 1) == "wN"
    assert board.is_empty(2, 0)
    assert events[0].destination == (0, 1)


# --- Layer C: interception is destination-only ------------------------------

def test_jumper_on_final_cell_intercepts_and_credits_the_jumper():
    arbiter, board = make_arbiter([["wR", "bP", "."]])
    arbiter.start_move("wR", (0, 0), ((0, 1),), True)
    arbiter.start_jump("bP", (0, 1))
    events = arbiter.advance_time(JD)

    assert board.get(0, 1) == "bP"     # target unchanged
    assert board.is_empty(0, 0)        # mover captured on its current cell
    assert len(events) == 1
    assert events[0].piece == "bP"
    assert events[0].captured == "wR"
    assert events[0].origin == events[0].destination == (0, 1)


def test_jumper_on_intermediate_cell_is_only_a_blocker_not_an_interceptor():
    """A jumping enemy mid-path does NOT capture the mover; the mover simply
    stops before it and settles on the cell it reached (interception stays
    destination-only)."""
    arbiter, board = make_arbiter([["wR", ".", "bP", "."]])
    arbiter.start_move("wR", (0, 0), ((0, 1), (0, 2), (0, 3)), True)
    arbiter.start_jump("bP", (0, 2))  # intermediate, not the final cell

    arbiter.advance_time(MD)          # steps to (0,1)
    events = arbiter.advance_time(MD)  # (0,2) holds an enemy jumper -> stop short

    assert board.get(0, 1) == "wR"    # mover survives, stopped short
    assert board.get(0, 2) == "bP"    # jumper untouched (not captured)
    assert board.is_empty(0, 3)
    assert events[0].captured is None
    assert events[0].destination == (0, 1)


# --- Layer C: promotion only fires at a real settle on the last rank --------

def test_pawn_promotes_when_it_settles_on_the_last_rank():
    arbiter, board = make_arbiter([["."], ["wP"]], promotion_rule=PromoteOnTopRank())
    arbiter.start_move("wP", (1, 0), ((0, 0),), False)
    events = arbiter.advance_time(MD)
    assert board.get(0, 0) == "wQ"
    assert events[0].piece == "wQ"


def test_pawn_blocked_short_of_last_rank_is_not_promoted():
    # row0 friendly blocker, pawn stops on row1 -> no promotion (wrong rank).
    arbiter, board = make_arbiter([["wR"], ["."], ["wP"]], promotion_rule=PromoteOnTopRank())
    arbiter.start_move("wP", (2, 0), ((1, 0), (0, 0)), False)
    arbiter.advance_time(MD)          # -> row1
    events = arbiter.advance_time(MD)  # row0 friendly blocks -> settle on row1
    assert board.get(1, 0) == "wP"    # NOT promoted (settled below the rank)
    assert events[0].piece == "wP"


def test_interception_never_promotes():
    """A pawn intercepted on the last rank is captured, not promoted: the event
    credits the jumper and no promotion rule runs on the interception branch."""
    arbiter, board = make_arbiter([["bN"], ["wP"]], promotion_rule=PromoteOnTopRank())
    arbiter.start_move("wP", (1, 0), ((0, 0),), False)  # heading to the top rank
    arbiter.start_jump("bN", (0, 0))
    events = arbiter.advance_time(JD)
    assert board.get(0, 0) == "bN"    # jumper stays, no wQ ever placed
    assert board.is_empty(1, 0)       # pawn captured off its current cell
    assert events[0].piece == "bN"
    assert events[0].captured == "wP"


# --- Layer C: is_mover_on keys off the CURRENT cell --------------------------

def test_is_mover_on_tracks_the_current_cell_not_the_source():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), ((0, 1), (0, 2)), True)
    assert arbiter.is_mover_on((0, 0)) is True   # still on source
    assert arbiter.is_mover_on((0, 1)) is False

    arbiter.advance_time(MD)  # step to (0,1)
    assert arbiter.is_mover_on((0, 0)) is False  # left the source
    assert arbiter.is_mover_on((0, 1)) is True   # now here


def test_is_jumping_on_reports_the_airborne_cell():
    arbiter, _ = make_arbiter([["wR", "bP", "."]])
    arbiter.start_jump("bP", (0, 1))
    assert arbiter.is_jumping_on((0, 1)) is True
    assert arbiter.is_jumping_on((0, 0)) is False


# --- Layer C: motion view interpolates the CURRENT sub-step -----------------

def test_motion_view_reports_half_progress_of_the_current_substep():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), ((0, 1), (0, 2)), True)

    arbiter.advance_time(MD // 2)  # halfway through the FIRST sub-step
    motion = arbiter.active_motions()[0]
    assert (motion.start, motion.end) == ((0, 0), (0, 1))
    assert motion.progress == 0.5

    arbiter.advance_time(MD - MD // 2)  # finish step 1 -> now on (0,1)
    arbiter.advance_time(MD // 2)       # halfway through the SECOND sub-step
    motion = arbiter.active_motions()[0]
    assert (motion.start, motion.end) == ((0, 1), (0, 2))
    assert motion.progress == 0.5
