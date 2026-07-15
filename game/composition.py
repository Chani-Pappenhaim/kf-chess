"""Shared composition root for the KungFu Chess GameEngine.

Single responsibility: assemble the GameEngine dependency graph in ONE place so
the two entry points do not each duplicate it. main.py (text command-script /
VPL grader) and play.py (graphical real-time loop) load their boards from
different formats but wire the exact same collaborators around them - RuleEngine,
RealTimeArbiter (with last-rank promotion), the king-capture win rule, the piece
registry, and optionally a Controller.

Board loading is deliberately left to each entry point (text vs CSV); these
helpers take an already-loaded board plus the registry that loaded it and build
everything else. The registry is exposed on its own because it is needed twice:
once to LOAD/validate the board and once inside the RuleEngine.
"""
from __future__ import annotations

from realtime.real_time_arbiter import RealTimeArbiter
from rules.rule_registry import build_default_registry
from rules.rule_engine import RuleEngine
from rules.game_conditions import KingCaptureWinCondition, LastRankPromotion
from game.engine import GameEngine
from game.board_mapper import BoardMapper
from game.controller import Controller


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
    RuleEngine (legality against `registry`), and the king-capture win rule.
    """
    arbiter = RealTimeArbiter(
        board=board,
        promotion_rule=LastRankPromotion(config.PAWN_DIRECTION),
        config=config,
    )
    return GameEngine(
        board=board,
        rule_engine=RuleEngine(rule_registry=registry, config=config),
        arbiter=arbiter,
        win_condition=KingCaptureWinCondition(),
        config=config,
    )


def build_game(board, registry, config):
    """build_engine plus a Controller wired with a BoardMapper.

    The full graph for an interactive entry point: returns the engine and a
    Controller that turns pixel clicks/jumps into engine commands.
    """
    engine = build_engine(board, registry, config)
    controller = Controller(engine, BoardMapper(board, config.CELL_SIZE))
    return engine, controller
