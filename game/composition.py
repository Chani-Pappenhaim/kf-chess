"""The one place the whole dependency graph is wired.

Both entry points load their board from a different format, then hand it here to
build everything else, so the wiring lives once instead of in each of them. The
registry is built separately because it is needed both to load the board and
inside the RuleEngine.
"""
from __future__ import annotations

from realtime.real_time_arbiter import RealTimeArbiter
from rules.rule_registry import build_default_registry
from rules.rule_engine import RuleEngine
from rules.game_conditions import KingCaptureWinCondition, LastRankPromotion
from game.engine import GameEngine
from game.board_mapper import BoardMapper
from game.controller import Controller
from game.move_log import MoveLog
from game.scoreboard import Scoreboard
from game.notation import CoordinateNotation
from game.observers import MoveRecorder, CaptureScorer


def build_registry(config):
    """The piece-rule registry the whole graph shares. Built first, used to load
    the board, then passed back in so the RuleEngine validates against it too."""
    return build_default_registry(config)


def build_engine(board, registry, config):
    """Wire the GameEngine around an already-loaded board.

    The log and the scoreboard are built here once and handed to both sides: to
    an observer that writes to them, and to the engine that exposes them to read.
    """
    arbiter = RealTimeArbiter(
        board=board,
        promotion_rule=LastRankPromotion(config.PAWN_DIRECTION),
        config=config,
    )
    move_log = MoveLog()
    scoreboard = Scoreboard(config.COLORS)
    return GameEngine(
        board=board,
        rule_engine=RuleEngine(rule_registry=registry, config=config),
        arbiter=arbiter,
        win_condition=KingCaptureWinCondition(),
        config=config,
        move_log=move_log,
        scoreboard=scoreboard,
        observers=(
            MoveRecorder(move_log, CoordinateNotation(board.height)),
            CaptureScorer(scoreboard, config.PIECE_VALUES),
        ),
    )


def build_game(board, registry, config, board_origin=(0, 0)):
    """build_engine plus a Controller, for an entry point that takes input.

    `board_origin` is the board's top-left pixel: (0, 0) for the text path, the
    framed offset for the graphical one, so clicks resolve to the right cell.
    """
    engine = build_engine(board, registry, config)
    controller = Controller(engine, BoardMapper(board, config.CELL_SIZE, board_origin))
    return engine, controller
