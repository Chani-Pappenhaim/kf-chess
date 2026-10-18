from concurrent.futures import Future

from bot.factory import ComputerPlayers, build_computer_players, build_strategy
from bot.player import ComputerPlayer
from bot.position import Position
from bot.strategy import GreedyStrategy
from config import settings
from tests.support import engine_with

KINGS = [("wK", (7, 4)), ("bK", (0, 4))]
INTERVAL = settings.BOT_MOVE_INTERVAL_MS


class Executor:
    """Runs each submitted call at once, unless `hold` is set - then hands
    back a Future the test completes itself, as a slow worker would."""

    def __init__(self, hold=False):
        self.hold = hold
        self.submitted = []
        self.futures = []

    def submit(self, fn, *args):
        self.submitted.append(args)
        future = Future()
        self.futures.append(future)
        if not self.hold:
            try:
                future.set_result(fn(*args))
            except Exception as error:
                future.set_exception(error)
        return future


class Fixed:
    def __init__(self, move):
        self.move = move

    def choose(self, position):
        return self.move


class Broken:
    def choose(self, position):
        raise RuntimeError("boom")


def player(engine, strategy, executor=None, report=None):
    return ComputerPlayer(engine, "b", strategy, executor or Executor(), settings,
                          report or (lambda message: None))


def test_the_computer_waits_out_the_interval_before_thinking():
    executor = Executor()
    bot = player(engine_with(KINGS), Fixed(((0, 4), (1, 4))), executor)
    bot.tick(INTERVAL - 1)
    assert executor.submitted == []
    bot.tick(1)
    assert len(executor.submitted) == 1


def test_a_chosen_move_is_played_on_the_next_tick():
    engine = engine_with(KINGS)
    bot = player(engine, Fixed(((0, 4), (1, 4))))
    bot.tick(INTERVAL)
    assert not engine.is_busy((0, 4))
    bot.tick(0)
    assert engine.is_busy((0, 4))


def test_the_computer_waits_for_a_slow_strategy_without_blocking():
    engine = engine_with(KINGS)
    executor = Executor(hold=True)
    bot = player(engine, Fixed(None), executor)
    bot.tick(INTERVAL)
    bot.tick(INTERVAL)              # still thinking: no second request
    assert len(executor.submitted) == 1


def test_a_slow_move_is_played_once_its_thinking_finishes():
    engine = engine_with(KINGS)
    executor = Executor(hold=True)
    bot = player(engine, Fixed(None), executor)
    bot.tick(INTERVAL)
    bot.tick(0)
    assert not engine.is_busy((0, 4))
    executor.futures[0].set_result(((0, 4), (1, 4)))   # the worker thread finishes
    bot.tick(0)
    assert engine.is_busy((0, 4))


def test_after_a_move_the_computer_waits_a_full_interval_again():
    executor = Executor()
    bot = player(engine_with(KINGS), Fixed(None), executor)
    bot.tick(INTERVAL)
    bot.tick(0)                     # plays (nothing), back to waiting
    bot.tick(INTERVAL - 1)
    assert len(executor.submitted) == 1
    bot.tick(1)
    assert len(executor.submitted) == 2


def test_a_strategy_with_nothing_to_offer_plays_nothing():
    engine = engine_with(KINGS)
    bot = player(engine, Fixed(None))
    bot.tick(INTERVAL)
    bot.tick(0)
    assert not engine.is_busy((0, 4))


def test_a_failing_strategy_costs_a_move_not_the_loop():
    reports = []
    engine = engine_with(KINGS)
    bot = player(engine, Broken(), report=reports.append)
    bot.tick(INTERVAL)
    bot.tick(0)
    assert len(reports) == 1 and "boom" in reports[0]
    assert not engine.is_busy((0, 4))


def test_a_move_from_a_square_that_changed_hands_is_dropped():
    engine = engine_with(KINGS)
    bot = player(engine, Fixed(((7, 4), (6, 4))))   # white's king, not ours
    bot.tick(INTERVAL)
    bot.tick(0)
    assert not engine.is_busy((7, 4))


def test_a_move_from_an_emptied_square_is_dropped():
    engine = engine_with(KINGS)
    bot = player(engine, Fixed(((3, 3), (2, 3))))
    bot.tick(INTERVAL)
    bot.tick(0)                                      # nothing to move, nothing raised


def test_the_computer_never_asks_when_it_has_no_free_piece():
    engine = engine_with(KINGS)
    engine.request_move((0, 4), (1, 4))              # its only piece is now moving
    executor = Executor()
    player(engine, Fixed(None), executor).tick(INTERVAL)
    assert executor.submitted == []


def test_the_computer_stops_once_the_game_is_over():
    engine = engine_with(KINGS)
    engine.concede("w", "resign")
    executor = Executor()
    player(engine, Fixed(((0, 4), (1, 4))), executor).tick(INTERVAL)
    assert executor.submitted == []


def test_a_player_knows_its_colour():
    assert player(engine_with(KINGS), Fixed(None)).color == "b"


class Config:
    """settings, with the Gemini key overridden."""

    def __init__(self, key):
        self.GEMINI_API_KEY = key

    def __getattr__(self, name):
        return getattr(settings, name)


def test_without_a_key_the_computer_plays_greedily():
    assert isinstance(build_strategy(Config("")), GreedyStrategy)


class Gemini:
    """A client whose every request fails, as an expired key would."""

    def __init__(self):
        self.models = self
        self.requests = 0

    def generate_content(self, **request):
        self.requests += 1
        raise ConnectionError("unreachable")


FREE_ROOK = Position(color="w", width=8, height=8, occupants={(7, 0): "wR"}, busy=(),
                     moves={(7, 0): ((6, 0),)})


def test_with_a_key_gemini_is_asked_first_and_greedy_covers_its_failures():
    client = Gemini()
    strategy = build_strategy(Config("key"), connect=lambda config: client)
    assert strategy.choose(FREE_ROOK) == ((7, 0), (6, 0))
    assert client.requests == 1


def test_a_key_without_a_client_falls_back_to_greedy():
    assert isinstance(build_strategy(Config("key"), connect=lambda config: None), GreedyStrategy)


def test_computer_players_share_one_strategy_and_one_pool():
    executor = Executor()
    players = ComputerPlayers(Fixed(None), executor, settings)
    engine = engine_with(KINGS)
    for bot in (players.player(engine, "w"), players.player(engine, "b")):
        bot.tick(INTERVAL)
    assert [position.color for (position,) in executor.submitted] == ["w", "b"]


def test_the_server_builds_its_computer_players_from_config():
    players = build_computer_players(Config(""))
    assert players.player(engine_with(KINGS), "b").color == "b"
