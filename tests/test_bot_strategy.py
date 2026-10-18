from bot.position import Position
from bot.strategy import FallbackStrategy, GreedyStrategy, StrategyError
from config import settings


def position(moves, occupants=None):
    return Position(color="w", width=8, height=8, occupants=occupants or {}, busy=(), moves=moves)


class FirstChoice:
    """An rng that always picks the first candidate, so ties are predictable."""

    def choice(self, options):
        return options[0]


class LastChoice:
    def choice(self, options):
        return options[-1]


def greedy(rng=None):
    return GreedyStrategy(settings.BOT_PIECE_VALUES, rng or FirstChoice())


def test_greedy_takes_the_most_valuable_piece_in_reach():
    board = position(
        moves={(7, 0): ((0, 0), (5, 0)), (7, 7): ((2, 7),)},
        occupants={(7, 0): "wR", (7, 7): "wR", (0, 0): "bN", (2, 7): "bQ"},
    )
    assert greedy().choose(board) == ((7, 7), (2, 7))


def test_greedy_takes_the_king_over_anything_else():
    board = position(
        moves={(7, 0): ((0, 0),), (7, 7): ((0, 7),)},
        occupants={(7, 0): "wR", (7, 7): "wR", (0, 0): "bQ", (0, 7): "bK"},
    )
    assert greedy().choose(board) == ((7, 7), (0, 7))


def test_greedy_breaks_ties_with_its_rng():
    board = position(moves={(7, 0): ((5, 0), (4, 0))}, occupants={(7, 0): "wR"})
    assert greedy(FirstChoice()).choose(board) == ((7, 0), (5, 0))
    assert greedy(LastChoice()).choose(board) == ((7, 0), (4, 0))


def test_greedy_has_nothing_to_offer_without_moves():
    assert greedy().choose(position(moves={})) is None


def test_greedy_plays_without_an_injected_rng():
    board = position(moves={(7, 0): ((5, 0),)}, occupants={(7, 0): "wR"})
    assert GreedyStrategy(settings.BOT_PIECE_VALUES).choose(board) == ((7, 0), (5, 0))


class Fixed:
    def __init__(self, move):
        self.move = move
        self.asked = 0

    def choose(self, position):
        self.asked += 1
        return self.move


class Broken:
    def choose(self, position):
        raise StrategyError("quota")


def test_fallback_uses_the_primarys_move_when_it_has_one():
    backup = Fixed(((1, 1), (2, 2)))
    chosen = FallbackStrategy(Fixed(((0, 0), (1, 0))), backup).choose(position({}))
    assert chosen == ((0, 0), (1, 0))
    assert backup.asked == 0


def test_fallback_asks_the_backup_when_the_primary_fails_and_reports_why():
    reports = []
    chosen = FallbackStrategy(Broken(), Fixed(((1, 1), (2, 2))), reports.append).choose(position({}))
    assert chosen == ((1, 1), (2, 2))
    assert len(reports) == 1 and "quota" in reports[0]


def test_fallback_asks_the_backup_when_the_primary_has_nothing():
    chosen = FallbackStrategy(Fixed(None), Fixed(((1, 1), (2, 2)))).choose(position({}))
    assert chosen == ((1, 1), (2, 2))
