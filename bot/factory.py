"""Wiring the computer player from config.

One strategy and one pool of worker threads serve every room on the server:
the Gemini quota belongs to the key, and threads are the server's to budget,
not each room's.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from bot.gemini import GeminiStrategy, SharedRateLimit
from bot.player import ComputerPlayer
from bot.strategy import FallbackStrategy, GreedyStrategy

_log = logging.getLogger("kfchess.bot")


class ComputerPlayers:
    """Makes the computer player for each room that seats one."""

    def __init__(self, strategy, executor, config):
        self._strategy = strategy
        self._executor = executor
        self._config = config

    def player(self, engine, color):
        return ComputerPlayer(engine, color, self._strategy, self._executor, self._config)


def build_strategy(config, connect=None):
    """Gemini with the greedy player behind it when a key is configured and a
    client can be made; the greedy player alone otherwise."""
    greedy = GreedyStrategy(config.BOT_PIECE_VALUES)
    if not config.GEMINI_API_KEY:
        return greedy
    client = (connect or connect_gemini)(config)
    if client is None:
        return greedy
    gemini = GeminiStrategy(client, SharedRateLimit(config.GEMINI_REQUESTS_PER_MINUTE), config)
    return FallbackStrategy(gemini, greedy)


def build_computer_players(config, connect=None):
    """The server's one set of computer players: a shared strategy and a pool
    of BOT_THREADS worker threads (started lazily, on the first move)."""
    executor = ThreadPoolExecutor(config.BOT_THREADS, thread_name_prefix="kfchess-bot")
    return ComputerPlayers(build_strategy(config, connect), executor, config)


def connect_gemini(config):  # pragma: no cover - needs the google-genai package and a real key
    """A google-genai client, or None (with a warning) when the package is
    missing - the computer still plays, greedily."""
    try:
        from google import genai
    except ImportError:
        _log.warning("GEMINI_API_KEY is set but google-genai is not installed; "
                     "the computer plays without Gemini")
        return None
    return genai.Client(api_key=config.GEMINI_API_KEY,
                        http_options={"timeout": config.GEMINI_TIMEOUT_MS})
