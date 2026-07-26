import play
from config import settings
from events.bus import EventBus
from game.events import GameEnded


def observed_engine():
    """An engine whose GameEnded events are collected as they publish."""
    bus, seen = EventBus(), []
    bus.subscribe(GameEnded, seen.append)
    return play.build_engine(settings, bus), seen


def test_conceding_ends_the_game_with_a_forfeit_winner():
    engine, seen = observed_engine()
    engine.concede("w", settings.GAME_END_FORFEIT)
    assert engine.game_over is True
    assert seen[0].winner == "w"
    assert seen[0].reason == settings.GAME_END_FORFEIT


def test_conceding_an_already_finished_game_does_nothing():
    engine, seen = observed_engine()
    engine.concede("w", settings.GAME_END_FORFEIT)
    engine.concede("b", settings.GAME_END_FORFEIT)  # the game is already over
    assert len(seen) == 1  # only the first concession took effect
