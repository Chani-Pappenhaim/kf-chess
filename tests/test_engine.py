from config import settings
from board.board import Board
from rules.rule_registry import build_default_registry
from rules.rule_engine import RuleEngine
from rules.game_conditions import (
    KingCaptureWinCondition,
    LastRankPromotion,
    WinCondition,
    PromotionRule,
)
from realtime.real_time_arbiter import RealTimeArbiter
from game.engine import GameEngine
from game.move_log import MoveLog
from game.scoreboard import Scoreboard
from game.notation import CoordinateNotation
from game.subscribers import MoveRecorder, CaptureScorer
from game.events import (
    GameStarted,
    MoveCompleted,
    PieceCaptured,
    JumpStarted,
    GameEnded,
)
from events.bus import EventBus
from rules.reasons import Reason
from view.renderer import BoardRenderer
from view.render_model import MOVE_STATE


class NeverEndsWinCondition(WinCondition):
    """Fake collaborator used to test engine behaviour in isolation,
    injected instead of monkeypatching KingCaptureWinCondition."""

    def is_game_over(self, captured_piece):
        return False


class NoPromotion(PromotionRule):
    def promote(self, piece, row, board_height):
        return piece


class _ConfigOverride:
    """Read-only view over the settings module with a few attributes replaced,
    so a test can flip a single policy (e.g. ALLOW_CONCURRENT_MOVES) without
    mutating the shared module. Any attribute not overridden falls through to
    the real settings."""

    def __init__(self, base, **overrides):
        self._base = base
        self._overrides = overrides

    def __getattr__(self, name):
        overrides = object.__getattribute__(self, "_overrides")
        if name in overrides:
            return overrides[name]
        return getattr(object.__getattribute__(self, "_base"), name)


def make_engine(rows, win_condition=None, promotion_rule=None, config=settings, bus=None):
    board = Board(rows, ".")
    registry = build_default_registry(config)
    arbiter = RealTimeArbiter(
        board=board,
        promotion_rule=promotion_rule or LastRankPromotion(config.PAWN_DIRECTION),
        config=config,
    )
    move_log = MoveLog()
    scoreboard = Scoreboard(config.COLORS)
    bus = bus or EventBus()
    bus.subscribe(MoveCompleted, MoveRecorder(move_log, CoordinateNotation(board.height)).record)
    bus.subscribe(PieceCaptured, CaptureScorer(scoreboard, config.PIECE_VALUES).award)
    engine = GameEngine(
        board=board,
        rule_engine=RuleEngine(rule_registry=registry, config=config),
        arbiter=arbiter,
        win_condition=win_condition or KingCaptureWinCondition(),
        config=config,
        move_log=move_log,
        scoreboard=scoreboard,
        bus=bus,
    )
    return engine, board


def test_request_move_starts_a_legal_move():
    engine, board = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]])
    result = engine.request_move((0, 0), (0, 2))

    assert result.is_accepted
    assert result.reason == Reason.OK
    assert board.get(0, 0) == "wR"  # piece stays at the source until it arrives


def test_a_command_does_not_advance_time_of_its_own():
    # Only wait() moves the clock, so a second command issued without a wait
    # cannot make the first move arrive early: the rook is still on its source
    # and a query mid-command settles nothing.
    engine, board = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]])
    engine.request_move((0, 0), (0, 2))
    engine.request_jump((2, 2))  # a second command, no wait between

    assert engine.clock == 0
    assert board.get(0, 0) == "wR"  # never arrived, because no time passed


def test_move_lands_after_move_duration_elapses():
    engine, board = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]])
    engine.request_move((0, 0), (0, 2))

    # A two-square move takes two move-durations to arrive.
    engine.wait(2 * settings.MOVE_DURATION)
    assert board.get(0, 2) == "wR"


def test_illegal_move_is_rejected_and_leaves_board_unchanged():
    engine, board = make_engine([["wN", ".", "."], [".", ".", "."], [".", ".", "."]])
    result = engine.request_move((0, 0), (0, 1))  # not a legal knight move

    assert not result.is_accepted
    assert result.reason == Reason.ILLEGAL_PIECE_MOVE
    assert board.get(0, 0) == "wN"


def test_friendly_destination_is_rejected():
    engine, board = make_engine([["wR", "wP", "."]])
    result = engine.request_move((0, 0), (0, 1))

    assert not result.is_accepted
    assert result.reason == Reason.FRIENDLY_DESTINATION


def test_second_move_while_one_is_active_is_rejected_in_strict_mode():
    strict = _ConfigOverride(settings, ALLOW_CONCURRENT_MOVES=False)
    rows = [["wR", ".", "."], [".", ".", "."], ["bR", ".", "."]]
    engine, board = make_engine(rows, config=strict)
    engine.request_move((0, 0), (0, 2))
    result = engine.request_move((2, 0), (2, 2))

    assert not result.is_accepted
    assert result.reason == Reason.MOTION_IN_PROGRESS


def test_both_players_can_have_moves_in_flight_at_once():
    # Real-time default: white and black may move simultaneously, so a second
    # move by the other player is accepted while the first is still travelling.
    rows = [["wR", ".", "."], [".", ".", "."], ["bR", ".", "."]]
    engine, board = make_engine(rows)
    engine.request_move((0, 0), (0, 2))
    result = engine.request_move((2, 0), (2, 2))

    assert result.is_accepted
    assert result.reason == Reason.OK

    engine.wait(2 * settings.MOVE_DURATION)
    assert board.get(0, 2) == "wR"
    assert board.get(2, 2) == "bR"


def test_same_player_can_start_another_move_while_one_is_in_flight():
    # A single player may move a second (different) piece before the first
    # arrives; only the piece already moving is "busy", the rest are free.
    rows = [["wR", ".", ".", "."], ["wN", ".", ".", "."], [".", ".", ".", "."]]
    engine, board = make_engine(rows)
    first = engine.request_move((0, 0), (0, 2))
    second = engine.request_move((1, 0), (2, 2))  # knight, a different piece

    assert first.is_accepted
    assert second.is_accepted

    engine.wait(2 * settings.MOVE_DURATION)
    assert board.get(0, 2) == "wR"
    assert board.get(2, 2) == "wN"


def test_a_busy_piece_cannot_start_a_second_move_even_when_concurrent():
    # Concurrency is per-piece: the same piece may not be launched twice while
    # its first move is still in flight.
    rows = [["wR", ".", "."], [".", ".", "."], [".", ".", "."]]
    engine, board = make_engine(rows)
    engine.request_move((0, 0), (0, 2))
    result = engine.request_move((0, 0), (2, 0))

    assert not result.is_accepted
    assert result.reason == Reason.BUSY_SOURCE


def test_king_capture_ends_the_game():
    rows = [["wR", ".", "bK"], [".", ".", "."], [".", ".", "."]]
    engine, board = make_engine(rows)
    engine.request_move((0, 0), (0, 2))
    engine.wait(2 * settings.MOVE_DURATION)

    assert engine.game_over is True


def test_move_after_game_over_is_rejected():
    rows = [["wR", ".", "bK"], ["bR", ".", "."], [".", ".", "."]]
    engine, board = make_engine(rows)
    engine.request_move((0, 0), (0, 2))
    engine.wait(2 * settings.MOVE_DURATION)

    result = engine.request_move((1, 0), (1, 1))
    assert not result.is_accepted
    assert result.reason == Reason.GAME_OVER


def test_injected_win_condition_overrides_default_behaviour():
    rows = [["wR", ".", "bK"], [".", ".", "."], [".", ".", "."]]
    engine, board = make_engine(rows, win_condition=NeverEndsWinCondition())
    engine.request_move((0, 0), (0, 2))
    engine.wait(2 * settings.MOVE_DURATION)

    assert engine.game_over is False


def test_jump_intercepts_a_move_of_the_opposite_color():
    # bP is adjacent so the one-square move (1000) and the jump (1000) land
    # together; otherwise the jump would expire before the move arrives.
    rows = [["wR", "bP", "."], [".", ".", "."], [".", ".", "."]]
    engine, board = make_engine(rows)
    engine.request_move((0, 0), (0, 1))
    engine.request_jump((0, 1))

    engine.wait(settings.JUMP_DURATION)
    assert board.get(0, 1) == "bP"  # move was intercepted, target unchanged
    assert board.is_empty(0, 0)  # the intercepted piece is captured mid-flight


def test_jump_on_empty_cell_is_rejected():
    engine, board = make_engine([[".", ".", "."], [".", ".", "."], [".", ".", "."]])
    result = engine.request_jump((1, 1))
    assert not result.is_accepted
    assert result.reason == Reason.EMPTY_CELL


def test_pawn_promotion_on_arrival():
    # white pawn one step from the last rank (row 0) is promoted to a queen
    rows = [[".", ".", "."], ["wP", ".", "."], [".", ".", "."]]
    engine, board = make_engine(rows)
    engine.request_move((1, 0), (0, 0))
    engine.wait(settings.MOVE_DURATION)

    assert board.get(0, 0) == "wQ"


def test_injected_promotion_rule_overrides_default_behaviour():
    rows = [[".", ".", "."], ["wP", ".", "."], [".", ".", "."]]
    engine, board = make_engine(rows, promotion_rule=NoPromotion())
    engine.request_move((1, 0), (0, 0))
    engine.wait(settings.MOVE_DURATION)

    assert board.get(0, 0) == "wP"


def test_render_returns_current_board_text():
    engine, board = make_engine([["wK", "."], [".", "bK"]])
    text = engine.render(BoardRenderer())
    assert text == "wK .\n. bK"


def test_move_from_a_resting_piece_is_rejected():
    engine, _ = make_engine([["wR", ".", "."]])
    engine.request_move((0, 0), (0, 1))
    engine.wait(settings.MOVE_DURATION)  # arrives at (0, 1), now resting
    result = engine.request_move((0, 1), (0, 2))
    assert not result.is_accepted
    assert result.reason == Reason.RESTING


def test_jump_from_a_piece_resting_after_a_move_is_rejected():
    engine, _ = make_engine([["wR", ".", "."]])
    engine.request_move((0, 0), (0, 1))
    engine.wait(settings.MOVE_DURATION)  # arrives at (0, 1), now in long_rest
    result = engine.request_jump((0, 1))
    assert not result.is_accepted
    assert result.reason == Reason.RESTING


def test_jump_from_a_piece_resting_after_a_jump_is_rejected():
    engine, _ = make_engine([["wR", ".", "."]])
    engine.request_jump((0, 0))
    engine.wait(settings.JUMP_DURATION)  # lands, now in short_rest
    result = engine.request_jump((0, 0))
    assert not result.is_accepted
    assert result.reason == Reason.RESTING


def test_a_resting_piece_is_not_selectable():
    engine, _ = make_engine([["wR", ".", "."]])
    engine.request_move((0, 0), (0, 1))
    engine.wait(settings.MOVE_DURATION)
    assert engine.render_model().selectable((0, 1)) is False


def test_cooldown_expires_and_the_piece_can_move_again():
    engine, _ = make_engine([["wR", ".", "."]])
    engine.request_move((0, 0), (0, 1))
    engine.wait(settings.MOVE_DURATION)
    engine.wait(settings.LONG_REST_DURATION)  # rest elapses
    assert engine.request_move((0, 1), (0, 2)).is_accepted


def test_render_model_marks_a_resting_piece():
    engine, _ = make_engine([["wR", ".", "."]])
    engine.request_move((0, 0), (0, 1))
    engine.wait(settings.MOVE_DURATION)
    resting = [p for p in engine.render_model().pieces if p.cell == (0, 1)]
    assert len(resting) == 1
    assert resting[0].state == "long_rest"


def test_clock_reflects_arbiter_time():
    engine, board = make_engine([["wR", ".", "."]])
    assert engine.clock == 0
    engine.wait(settings.MOVE_DURATION)
    assert engine.clock == settings.MOVE_DURATION


def test_busy_source_is_rejected_while_that_piece_is_moving():
    engine, board = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]])
    engine.request_move((0, 0), (0, 2))  # in flight, source (0,0) busy
    result = engine.request_move((0, 0), (0, 1))
    assert not result.is_accepted
    assert result.reason == Reason.BUSY_SOURCE


def test_nothing_is_selectable_after_game_over():
    rows = [["wR", ".", "bK"], ["bR", ".", "."], [".", ".", "."]]
    engine, board = make_engine(rows)
    engine.request_move((0, 0), (0, 2))
    engine.wait(2 * settings.MOVE_DURATION)  # captures bK -> game over
    assert engine.render_model().selectable((1, 0)) is False


def test_jump_after_game_over_is_rejected():
    rows = [["wR", ".", "bK"], ["bR", ".", "."], [".", ".", "."]]
    engine, board = make_engine(rows)
    engine.request_move((0, 0), (0, 2))
    engine.wait(2 * settings.MOVE_DURATION)
    result = engine.request_jump((1, 0))
    assert not result.is_accepted
    assert result.reason == Reason.GAME_OVER


def test_jump_on_busy_cell_is_rejected():
    engine, board = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]])
    engine.request_move((0, 0), (0, 2))  # (0,0) now busy
    result = engine.request_jump((0, 0))
    assert not result.is_accepted
    assert result.reason == Reason.BUSY_CELL


def test_legal_targets_lists_moves_for_a_piece():
    engine, _ = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]])
    assert set(engine.legal_targets((0, 0))) == {(0, 1), (0, 2), (1, 0), (2, 0)}


def test_legal_targets_is_empty_after_game_over():
    rows = [["wR", ".", "bK"], ["wN", ".", "."], [".", ".", "."]]
    engine, _ = make_engine(rows)
    engine.request_move((0, 0), (0, 2))
    engine.wait(2 * settings.MOVE_DURATION)  # captures bK -> game over
    assert engine.legal_targets((1, 0)) == ()  # the knight can no longer be hinted


def test_completed_move_is_recorded_in_the_move_log():
    # 3-row board, so row 0 is rank 3: wR a3 -> c3.
    engine, _ = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]])
    engine.request_move((0, 0), (0, 2))
    engine.wait(2 * settings.MOVE_DURATION)

    entries = engine.move_log.entries("w")
    assert len(entries) == 1
    assert entries[0].notation == "Ra3-c3"
    assert entries[0].color == "w"
    assert entries[0].time_ms == 2 * settings.MOVE_DURATION


def subscribe_all(bus):
    """Record every published event, in the order the engine published it."""
    seen = []
    for event_type in (GameStarted, MoveCompleted, PieceCaptured, GameEnded, JumpStarted):
        bus.subscribe(event_type, seen.append)
    return seen


def test_a_piece_stops_being_selectable_the_instant_it_is_commanded():
    # No time has passed and the piece has not travelled a pixel, but the
    # arbiter already holds the motion - so the model reports it as moving
    # rather than idle, and there is no window in which it reads as free.
    engine, _ = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]])
    assert engine.render_model().selectable((0, 0)) is True

    engine.request_move((0, 0), (0, 2))
    model = engine.render_model()
    assert model.selectable((0, 0)) is False
    assert model.pieces[0].state == MOVE_STATE
    assert model.pieces[0].progress == 0.0


def test_a_jumping_piece_stops_being_selectable_at_take_off():
    engine, _ = make_engine([["wR", ".", "."]])
    engine.request_jump((0, 0))
    assert engine.render_model().selectable((0, 0)) is False


def test_a_moving_piece_is_listed_on_the_cell_it_occupies():
    # Mid-move, with the mover one step short of an enemy: it must be listed on
    # the square it has reached, not on the one it is heading into - otherwise
    # two pieces would share a cell and occupancy could not be read off the
    # model at all.
    engine, _ = make_engine([["wR", ".", "bP"], [".", ".", "."], [".", ".", "."]])
    engine.request_move((0, 0), (0, 2))
    engine.wait(settings.MOVE_DURATION + settings.MOVE_DURATION // 2)

    pieces = engine.render_model().pieces
    cells = [piece.cell for piece in pieces]
    assert sorted(cells) == [(0, 1), (0, 2)]
    assert len(cells) == len(set(cells))
    mover = next(piece for piece in pieces if piece.state == "move")
    assert (mover.cell, mover.target) == ((0, 1), (0, 2))


def test_a_completed_move_is_published():
    # The extension point: a new consumer attaches without the engine knowing
    # anything about it.
    bus = EventBus()
    seen = []
    bus.subscribe(MoveCompleted, seen.append)
    engine, _ = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]], bus=bus)
    engine.request_move((0, 0), (0, 2))
    engine.wait(2 * settings.MOVE_DURATION)

    assert len(seen) == 1
    assert seen[0].destination == (0, 2)
    assert seen[0].at_ms == 2 * settings.MOVE_DURATION


def test_a_move_without_a_capture_publishes_no_capture():
    bus = EventBus()
    seen = []
    bus.subscribe(PieceCaptured, seen.append)
    engine, _ = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]], bus=bus)
    engine.request_move((0, 0), (0, 2))
    engine.wait(2 * settings.MOVE_DURATION)

    assert seen == []


def test_an_arrival_publishes_its_events_from_the_specific_to_the_general():
    # The guaranteed order: no subscriber sees a conclusion before its cause.
    bus = EventBus()
    seen = subscribe_all(bus)
    engine, _ = make_engine([["wR", ".", "bK"], [".", ".", "."], [".", ".", "."]], bus=bus)
    engine.request_move((0, 0), (0, 2))
    engine.wait(2 * settings.MOVE_DURATION)

    assert [type(event) for event in seen] == [MoveCompleted, PieceCaptured, GameEnded]
    assert seen[1].captor == "wR" and seen[1].captured == "bK"
    assert seen[2].winner == "w"


def test_the_game_ends_once_however_many_kings_fall_together():
    # Both sides can be in flight at once, so two arrivals may end the game in
    # the same batch - the second is not a second ending.
    bus = EventBus()
    seen = []
    bus.subscribe(GameEnded, seen.append)
    engine, _ = make_engine(
        [["wR", ".", "bK"], [".", ".", "."], ["bR", ".", "wK"]], bus=bus
    )
    engine.request_move((0, 0), (0, 2))
    engine.request_move((2, 0), (2, 2))
    engine.wait(2 * settings.MOVE_DURATION)

    assert len(seen) == 1


def test_start_announces_the_game_is_open():
    bus = EventBus()
    seen = []
    bus.subscribe(GameStarted, seen.append)
    engine, _ = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]], bus=bus)
    engine.start()

    assert len(seen) == 1


def test_a_jump_is_published_immediately():
    # A jump is reported the instant it is accepted, not on landing, so a
    # listener (e.g. a sound) reacts at take-off.
    bus = EventBus()
    seen = []
    bus.subscribe(JumpStarted, seen.append)
    engine, _ = make_engine([["wR", ".", "."], [".", ".", "."], [".", ".", "."]], bus=bus)
    engine.request_jump((0, 0))

    assert len(seen) == 1
    assert seen[0].piece == "wR"
    assert seen[0].cell == (0, 0)


def test_capture_is_recorded_with_x_and_awards_material():
    engine, _ = make_engine([["wR", ".", "bP"], [".", ".", "."], [".", ".", "."]])
    engine.request_move((0, 0), (0, 2))  # rook captures the black pawn
    engine.wait(2 * settings.MOVE_DURATION)

    assert engine.move_log.entries("w")[0].notation == "Ra3xc3"
    assert engine.scoreboard.score("w") == settings.PIECE_VALUES["P"]
    assert engine.scoreboard.score("b") == 0


def test_intercepted_move_is_recorded_and_scored_for_the_jumper():
    # The move is captured mid-flight by the jump. The jumping piece is credited
    # with the capture, so it is recorded in the log and scores the mover's value.
    engine, _ = make_engine([["wR", "bP", "."], [".", ".", "."], [".", ".", "."]])
    engine.request_move((0, 0), (0, 1))
    engine.request_jump((0, 1))
    engine.wait(settings.JUMP_DURATION)

    assert engine.scoreboard.score("b") == settings.PIECE_VALUES["R"]
    assert engine.scoreboard.score("w") == 0
    black_entries = engine.move_log.entries("b")
    assert len(black_entries) == 1
    assert black_entries[0].notation == "xb3"  # pawn capture in place on b3


def test_blocked_pawn_stops_on_the_last_square_it_reached():
    # The headline step-movement case. A pawn double-steps b2->b4 (through b3)
    # while a friendly queen a4->b4 lands on the destination first. The pawn
    # advances one square to b3, finds the destination occupied by a friendly
    # piece, and MUST stop on b3 - it must NOT snap back to its source b2 (the
    # old atomic behaviour), and it must not capture straight ahead.
    rows = [
        ["wQ", ".", "."],
        [".", ".", "."],
        [".", "wP", "."],
        [".", ".", "."],
    ]
    engine, board = make_engine(rows)
    engine.request_move((2, 1), (0, 1))  # pawn double step b2 -> b4
    engine.request_move((0, 0), (0, 1))  # friendly queen a4 -> b4, arrives first

    engine.wait(2 * settings.MOVE_DURATION)

    assert board.get(1, 1) == "wP"   # stopped on the mid square (b3)
    assert board.is_empty(2, 1)      # it left its source and did NOT snap back
    assert board.get(0, 1) == "wQ"   # the friendly queen was not captured
    # The partial advance is a real, recorded move ending on the square it
    # actually reached - not the destination it was aiming for.
    entries = engine.move_log.entries("w")
    pawn_entry = [e for e in entries if e.notation == "b2-b3"]
    assert len(pawn_entry) == 1


def test_slider_stops_when_a_friendly_piece_crosses_its_path():
    # Cross-traffic blocking, which falls out of the same stepping mechanism.
    # A rook climbs column c (c1->c5) while a same-colour queen crosses row 3
    # (a3->e3). The queen reaches the intersection c3 the moment the rook tries
    # to enter it; because the queen was requested first it claims c3, so the
    # rook is stuck one square up from its source, at c2.
    rows = [
        [".", ".", ".", ".", "."],
        [".", ".", ".", ".", "."],
        ["wQ", ".", ".", ".", "."],
        [".", ".", ".", ".", "."],
        [".", ".", "wR", ".", "."],
    ]
    engine, board = make_engine(rows)
    engine.request_move((2, 0), (2, 4))  # queen a3 -> e3 (requested first)
    engine.request_move((4, 2), (0, 2))  # rook c1 -> c5

    engine.wait(5 * settings.MOVE_DURATION)

    assert board.get(3, 2) == "wR"   # rook stuck at c2 (one square up from c1)
    assert board.is_empty(4, 2)      # rook left its source, did not snap back
    assert board.get(2, 4) == "wQ"   # the queen completed its crossing
    assert engine.move_log.entries("w")  # both moves recorded


def test_snapshot_is_readonly_view_of_state():
    engine, board = make_engine([["wK", "."], [".", "bK"]])
    snap = engine.snapshot()
    assert snap.cells == (("wK", "."), (".", "bK"))
    assert snap.width == 2 and snap.height == 2
    assert snap.game_over is False
    assert snap.selected is None
