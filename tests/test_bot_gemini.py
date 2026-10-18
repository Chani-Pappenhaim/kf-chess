from types import SimpleNamespace

import pytest

from bot.gemini import GeminiStrategy, SharedRateLimit, describe, read_move
from bot.position import Position
from bot.strategy import StrategyError
from config import settings

BOARD = Position(
    color="w", width=8, height=8,
    occupants={(7, 0): "wR", (7, 4): "wK", (0, 4): "bK", (0, 0): "bQ"},
    busy=(("bQ", (0, 0), "short_rest"),),
    moves={(7, 0): ((0, 0), (6, 0)), (7, 4): ((6, 4),)},
)


def call(from_square, to_square):
    return SimpleNamespace(name="make_move", args={"from_square": from_square, "to_square": to_square})


def reply(*calls):
    """A response shaped as google-genai returns one."""
    return SimpleNamespace(function_calls=list(calls),
                           candidates=[SimpleNamespace(content={"role": "model", "calls": calls})])


class FakeGemini:
    """Answers generate_content with the replies it is given, in order, and
    keeps every request for the test to read."""

    def __init__(self, *replies):
        self._replies = list(replies)
        self.requests = []
        self.models = self

    def generate_content(self, model, contents, config):
        self.requests.append({"model": model, "contents": list(contents), "config": config})
        return self._replies.pop(0)


class Limit:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def allow(self):
        return self.allowed


def gemini(client, limit=None):
    return GeminiStrategy(client, limit or Limit(), settings)


def test_a_legal_move_named_by_gemini_is_played():
    assert gemini(FakeGemini(reply(call("a1", "a8")))).choose(BOARD) == ((7, 0), (0, 0))


def test_the_request_forces_the_make_move_tool_and_names_the_model():
    client = FakeGemini(reply(call("a1", "a8")))
    gemini(client).choose(BOARD)
    request = client.requests[0]
    assert request["model"] == settings.GEMINI_MODEL
    assert request["config"]["tool_config"] == {"function_calling_config": {"mode": "ANY"}}
    assert request["config"]["automatic_function_calling"] == {"disable": True}
    assert request["config"]["tools"][0]["function_declarations"][0]["name"] == "make_move"
    assert "a1 (wR): a8, a2" in request["contents"][0]["parts"][0]["text"]


def test_an_illegal_move_is_sent_back_and_gemini_may_try_again():
    client = FakeGemini(reply(call("a1", "b2")), reply(call("e1", "e2")))
    assert gemini(client).choose(BOARD) == ((7, 4), (6, 4))
    retry = client.requests[1]["contents"]
    assert len(retry) == 3
    error = retry[2]["parts"][0]["function_response"]
    assert error["name"] == "make_move" and "not one of your legal moves" in error["response"]["error"]


def test_every_call_in_a_refused_reply_is_answered():
    client = FakeGemini(reply(call("a1", "b2"), call("zz", "")), reply(call("a1", "a2")))
    gemini(client).choose(BOARD)
    assert len(client.requests[1]["contents"][2]["parts"]) == 2


def test_gemini_gives_up_after_the_configured_number_of_replies():
    client = FakeGemini(*[reply(call("a1", "b2")) for _ in range(settings.GEMINI_MAX_ATTEMPTS)])
    with pytest.raises(StrategyError):
        gemini(client).choose(BOARD)
    assert len(client.requests) == settings.GEMINI_MAX_ATTEMPTS


def test_a_reply_without_a_function_call_fails():
    no_call = SimpleNamespace(function_calls=None, candidates=[])
    with pytest.raises(StrategyError):
        gemini(FakeGemini(no_call)).choose(BOARD)


def test_a_throttled_request_fails_without_calling_gemini():
    client = FakeGemini()
    with pytest.raises(StrategyError):
        gemini(client, Limit(allowed=False)).choose(BOARD)
    assert client.requests == []


def test_no_moves_means_no_request():
    client = FakeGemini()
    empty = Position(color="w", width=8, height=8, occupants={}, busy=(), moves={})
    assert gemini(client).choose(empty) is None
    assert client.requests == []


def test_the_description_shows_the_colour_board_busy_pieces_and_moves():
    text = describe(BOARD)
    assert text.splitlines()[0] == "You play white."
    assert " 8 bQ  .  .  . bK  .  .  ." in text
    assert " 1 wR  .  .  . wK  .  .  ." in text
    assert "bQ on a8 (short_rest)" in text
    assert text.endswith("a1 (wR): a8, a2\ne1 (wK): e2")


def test_the_description_omits_the_busy_line_when_nothing_is_busy():
    calm = Position(color="b", width=8, height=8, occupants={(0, 4): "bK"}, busy=(),
                    moves={(0, 4): ((1, 4),)})
    assert "Busy" not in describe(calm)
    assert describe(calm).startswith("You play black.")


@pytest.mark.parametrize("arguments", [{}, {"from_square": "a", "to_square": "a8"},
                                       {"from_square": "a1", "to_square": "ax"}])
def test_unreadable_squares_are_a_problem_not_a_crash(arguments):
    move, problem = read_move(BOARD, arguments)
    assert move is None and "Could not read" in problem


def test_shared_rate_limit_allows_its_quota_then_refills_over_time():
    now = [0.0]
    limit = SharedRateLimit(2, clock=lambda: now[0])
    assert limit.allow() and limit.allow()
    assert not limit.allow()
    now[0] = 30.0       # 2 per minute: one token back every 30 seconds
    assert limit.allow()
