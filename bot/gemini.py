"""Moves from Gemini, through function calling.

The model is shown the board and every legal move in one message, and given a
single tool, `make_move`, which it is required to call (function-calling mode
ANY) - so almost every move costs exactly one request, which is what the free
tier's per-minute limit can afford. A move it names that is not on the list is
sent back as the tool's error and it may try again, up to GEMINI_MAX_ATTEMPTS
replies in all.

The client is injected (bot/factory.py builds the real google-genai one), so
everything here runs in tests against a fake that answers as Gemini would.
"""
from __future__ import annotations

import threading
import time

from bot.strategy import StrategyError
from game.squares import SquareError, cell_of, square_of
from server.rate_limit import TokenBucket

EMPTY_MARK = "."
COLOR_NAMES = {"w": "white", "b": "black"}

SYSTEM_PROMPT = """You are playing KungFu Chess. It differs from normal chess:
- There are no turns. Both players move whenever they like.
- A move takes time: the piece slides square by square, then rests before it
  can move again. Busy pieces cannot move.
- You win by capturing the enemy king. There is no check or checkmate.
Each message shows the board and your legal moves. Call make_move once, with a
strong move from that list: capture undefended pieces, do not leave your own
pieces hanging, and keep your king safe."""

MAKE_MOVE = {
    "name": "make_move",
    "description": "Move one of your pieces, e.g. from 'e7' to 'e5'.",
    "parameters": {
        "type": "object",
        "properties": {
            "from_square": {"type": "string", "description": "Square of your piece, e.g. 'e7'"},
            "to_square": {"type": "string", "description": "Destination square, e.g. 'e5'"},
        },
        "required": ["from_square", "to_square"],
    },
}


class SharedRateLimit:
    """One token bucket for every room's worker thread: the per-minute quota
    belongs to the API key, not to a room. Locked, since TokenBucket itself is
    written for a single thread."""

    def __init__(self, per_minute, clock=time.monotonic):
        self._bucket = TokenBucket(per_minute, per_minute / 60, clock)
        self._lock = threading.Lock()

    def allow(self):
        with self._lock:
            return self._bucket.allow()


class GeminiStrategy:
    def __init__(self, client, limit, config):
        self._client = client
        self._limit = limit
        self._config = config
        self._request = {
            "system_instruction": SYSTEM_PROMPT,
            "tools": [{"function_declarations": [MAKE_MOVE]}],
            "tool_config": {"function_calling_config": {"mode": "ANY"}},
            "automatic_function_calling": {"disable": True},
            "thinking_config": {"thinking_budget": config.GEMINI_THINKING_BUDGET},
        }

    def choose(self, position):
        if not position.moves:
            return None
        contents = [{"role": "user", "parts": [{"text": describe(position)}]}]
        for _ in range(self._config.GEMINI_MAX_ATTEMPTS):
            if not self._limit.allow():
                raise StrategyError("Gemini request rate limit reached")
            response = self._client.models.generate_content(
                model=self._config.GEMINI_MODEL, contents=contents, config=self._request,
            )
            calls = response.function_calls or []
            if not calls:
                raise StrategyError("Gemini answered without calling make_move")
            move, problem = read_move(position, dict(calls[0].args or {}))
            if move is not None:
                return move
            # Every call in the reply is answered, as the API requires; only
            # the first was read, so they all carry its problem.
            contents.append(response.candidates[0].content)
            contents.append({"role": "user", "parts": [_reply(call, problem) for call in calls]})
        raise StrategyError(f"no legal move from Gemini in {self._config.GEMINI_MAX_ATTEMPTS} replies")


def describe(position):
    """The board, the busy pieces and the legal moves, as the model reads them."""
    grid = [[EMPTY_MARK] * position.width for _ in range(position.height)]
    for (row, col), token in position.occupants.items():
        grid[row][col] = token
    files = "   " + " ".join(f"{chr(ord('a') + col):>2}" for col in range(position.width))
    rows = [
        f"{position.height - row:>2} " + " ".join(f"{token:>2}" for token in grid[row])
        for row in range(position.height)
    ]
    lines = [f"You play {COLOR_NAMES[position.color]}.", files, *rows]
    if position.busy:
        lines.append("Busy pieces (cannot move now): " + "; ".join(
            f"{token} on {square_of(cell, position.height)} ({state})"
            for token, cell, state in position.busy
        ))
    lines.append("Your legal moves:")
    for start, targets in sorted(position.moves.items()):
        squares = ", ".join(square_of(end, position.height) for end in targets)
        lines.append(f"{square_of(start, position.height)} ({position.occupants[start]}): {squares}")
    return "\n".join(lines)


def read_move(position, arguments):
    """The (start, end) cells a make_move call names, or (None, why not)."""
    from_square = str(arguments.get("from_square", ""))
    to_square = str(arguments.get("to_square", ""))
    try:
        start = cell_of(from_square, position.height)
        end = cell_of(to_square, position.height)
    except SquareError:
        return None, f"Could not read squares '{from_square}' -> '{to_square}'."
    if not position.is_legal(start, end):
        return None, f"{from_square} -> {to_square} is not one of your legal moves. Pick one from the list."
    return (start, end), None


def _reply(call, problem):
    return {"function_response": {"name": call.name, "response": {"error": problem}}}
