from config import settings
from board.board import Board
from rules.game_conditions import LastRankPromotion, PromotionRule
from realtime.real_time_arbiter import RealTimeArbiter


class NoPromotion(PromotionRule):
    def promote(self, piece, row, board_height):
        return piece


def make_arbiter(rows, promotion_rule=None):
    board = Board(rows)
    arbiter = RealTimeArbiter(
        board=board,
        promotion_rule=promotion_rule or NoPromotion(),
        config=settings,
    )
    return arbiter, board


def test_active_motions_report_progress_along_the_move():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), (0, 2))  # 2 squares
    arbiter.advance_time(settings.MOVE_DURATION)  # halfway (of 2 * duration)

    motions = arbiter.active_motions()
    assert len(motions) == 1
    motion = motions[0]
    assert (motion.piece, motion.start, motion.end) == ("wR", (0, 0), (0, 2))
    assert motion.progress == 0.5


def test_active_motions_is_empty_when_nothing_moves():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    assert arbiter.active_motions() == []


def test_completed_move_leaves_a_long_rest_cooldown():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), (0, 1))
    arbiter.advance_time(settings.MOVE_DURATION)  # arrives at (0, 1)
    assert arbiter.cooldown_of((0, 1)) == "long_rest"
    assert arbiter.is_resting((0, 1))


def test_jump_stays_airborne_before_its_duration():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_jump("wR", (0, 0))
    arbiter.advance_time(settings.JUMP_DURATION - 1)
    assert arbiter.is_jumping_on((0, 0))
    assert arbiter.cooldown_of((0, 0)) is None  # airborne, not resting yet


def test_completed_jump_leaves_a_short_rest_cooldown():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_jump("wR", (0, 0))
    arbiter.advance_time(settings.JUMP_DURATION)  # jump ends on (0, 0)
    assert arbiter.cooldown_of((0, 0)) == "short_rest"


def test_cooldown_clears_after_its_duration():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), (0, 1))
    arbiter.advance_time(settings.MOVE_DURATION)
    arbiter.advance_time(settings.LONG_REST_DURATION)  # rest elapses
    assert arbiter.cooldown_of((0, 1)) is None
    assert not arbiter.is_resting((0, 1))


def test_cooldown_progress_rises_from_zero_to_one_across_the_rest():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), (0, 1))
    arbiter.advance_time(settings.MOVE_DURATION)  # arrives, long rest begins
    assert arbiter.cooldown_progress((0, 1)) == 0.0

    arbiter.advance_time(settings.LONG_REST_DURATION // 2)  # about halfway
    halfway = arbiter.cooldown_progress((0, 1))
    assert 0.4 < halfway < 0.6

    arbiter.advance_time(settings.LONG_REST_DURATION)  # well past the end
    assert arbiter.cooldown_progress((0, 1)) is None


def test_cooldown_progress_is_none_when_not_resting():
    arbiter, _ = make_arbiter([["wR", ".", "."]])
    assert arbiter.cooldown_progress((0, 0)) is None


def test_one_square_move_has_not_arrived_before_duration():
    arbiter, board = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), (0, 1))
    arbiter.advance_time(settings.MOVE_DURATION - 1)

    assert board.get(0, 0) == "wR"  # still at source
    assert board.is_empty(0, 1)
    assert arbiter.has_active_motion() is True


def test_one_square_move_arrives_at_duration():
    arbiter, board = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), (0, 1))
    events = arbiter.advance_time(settings.MOVE_DURATION)

    assert board.is_empty(0, 0)
    assert board.get(0, 1) == "wR"
    assert arbiter.has_active_motion() is False
    assert len(events) == 1
    assert events[0].destination == (0, 1)
    assert events[0].captured is None


def test_arrival_time_scales_with_distance():
    arbiter, board = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), (0, 2))  # two squares -> 2000ms
    arbiter.advance_time(settings.MOVE_DURATION)
    assert board.get(0, 0) == "wR"  # not yet arrived after one duration
    arbiter.advance_time(settings.MOVE_DURATION)
    assert board.get(0, 2) == "wR"


def test_partial_waits_accumulate():
    arbiter, board = make_arbiter([["wR", ".", "."]])
    arbiter.start_move("wR", (0, 0), (0, 1))
    arbiter.advance_time(settings.MOVE_DURATION // 2)
    arbiter.advance_time(settings.MOVE_DURATION - settings.MOVE_DURATION // 2)
    assert board.get(0, 1) == "wR"


def test_capture_reported_on_arrival():
    arbiter, board = make_arbiter([["wR", ".", "bK"]])
    arbiter.start_move("wR", (0, 0), (0, 2))
    events = arbiter.advance_time(2 * settings.MOVE_DURATION)
    assert board.get(0, 2) == "wR"
    assert events[0].captured == "bK"


def test_promotion_applied_on_arrival():
    arbiter, board = make_arbiter(
        [[".", ".", "."], ["wP", ".", "."]],
        promotion_rule=LastRankPromotion(settings.PAWN_DIRECTION),
    )
    arbiter.start_move("wP", (1, 0), (0, 0))
    events = arbiter.advance_time(settings.MOVE_DURATION)
    assert board.get(0, 0) == "wQ"
    assert events[0].piece == "wQ"


def test_jump_intercepts_arriving_enemy_and_emits_no_event():
    arbiter, board = make_arbiter([["wR", "bP", "."]])
    arbiter.start_move("wR", (0, 0), (0, 1))
    arbiter.start_jump("bP", (0, 1))
    events = arbiter.advance_time(settings.JUMP_DURATION)

    assert board.get(0, 1) == "bP"  # target unchanged
    assert board.is_empty(0, 0)  # mover captured mid-flight
    assert events == []


def test_friendly_piece_at_destination_cancels_arrival():
    # If a friendly piece occupies the destination on arrival, the mover does
    # not land and no event is emitted.
    arbiter, board = make_arbiter([["wR", ".", "."], ["wP", ".", "."]])
    arbiter.start_move("wR", (0, 0), (0, 2))
    # Drop a friendly piece on the destination before arrival.
    board.set(0, 2, "wP")
    events = arbiter.advance_time(2 * settings.MOVE_DURATION)
    assert board.get(0, 0) == "wR"  # mover survives in place
    assert board.get(0, 2) == "wP"
    assert events == []


def test_clock_advances_with_time():
    arbiter, board = make_arbiter([["wR", ".", "."]])
    assert arbiter.clock == 0
    arbiter.advance_time(250)
    assert arbiter.clock == 250


def test_is_moving_from_and_is_jumping_on():
    arbiter, board = make_arbiter([["wR", "bP", "."]])
    arbiter.start_move("wR", (0, 0), (0, 2))
    arbiter.start_jump("bP", (0, 1))
    assert arbiter.is_moving_from((0, 0)) is True
    assert arbiter.is_moving_from((0, 2)) is False
    assert arbiter.is_jumping_on((0, 1)) is True
