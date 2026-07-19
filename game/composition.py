"""Shared composition root for the GameEngine.

Single responsibility: assemble the dependency graph in ONE place so the two
entry points do not each duplicate it. The text command-script (main.py) and the
graphical real-time loop (play.py) load their boards from different formats but
wire the exact same collaborators around them - RuleEngine, RealTimeArbiter,
the win rule, the event observers, and optionally a Controller.

Board loading is deliberately left to each entry point; these helpers take an
already-loaded board plus the registry that loaded it and build everything else.
The registry is exposed on its own because it is needed twice: once to
LOAD/validate the board and once inside the RuleEngine.
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
    """The piece-rule registry the whole graph shares.

    Callers build it first, use it to load/validate their board (text or CSV),
    then pass it back into build_engine/build_game so the RuleEngine validates
    against the same piece set the board was parsed with.
    """
    return build_default_registry(config)


def build_engine(board, registry, config):
    """Wire the GameEngine around an already-loaded board.

    Assembles the RealTimeArbiter (owning motion and last-rank promotion), the
    RuleEngine (legality against `registry`), the king-capture win rule, and the
    observers that react to completed moves. The log and the scoreboard are
    created here once and handed to both sides: to an observer that writes to
    them, and to the engine that exposes them for reading.
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
    """build_engine plus a Controller wired with a BoardMapper.

    The full graph for an interactive entry point: returns the engine and a
    Controller that turns pixel clicks/jumps into engine commands. `board_origin`
    is the board's top-left pixel on the canvas; it defaults to (0, 0) for the
    text path (board-local click coordinates) and is set by the graphical entry
    point to the framed board's offset.
    """
    engine = build_engine(board, registry, config)
    controller = Controller(engine, BoardMapper(board, config.CELL_SIZE, board_origin))
    return engine, controller
