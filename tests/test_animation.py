from config import settings
from events.bus import EventBus
from game.events import GameStarted, GameEnded
from ui.animation import BannerAnimation, subscribe_banner


def test_nothing_shows_before_any_event():
    assert BannerAnimation(settings).text_at(0) is None


def test_the_start_banner_shows_when_the_game_opens():
    banner = BannerAnimation(settings)
    banner.announce_start(GameStarted(at_ms=0))
    assert banner.text_at(0) == settings.START_BANNER_TEXT


def test_the_start_banner_clears_itself():
    banner = BannerAnimation(settings)
    banner.announce_start(GameStarted(at_ms=0))
    assert banner.text_at(settings.START_BANNER_MS) is None


def test_the_start_banner_is_timed_from_the_event_not_from_zero():
    banner = BannerAnimation(settings)
    banner.announce_start(GameStarted(at_ms=4000))
    assert banner.text_at(4000 + settings.START_BANNER_MS - 1) is not None


def test_the_end_banner_names_the_winner_and_stays():
    banner = BannerAnimation(settings)
    banner.announce_end(GameEnded(winner="b", at_ms=9000))
    assert banner.text_at(9000) == "BLACK WINS"
    assert banner.text_at(9000 + 10 ** 9) == "BLACK WINS"


def test_the_end_banner_replaces_the_start_banner():
    banner = BannerAnimation(settings)
    banner.announce_start(GameStarted(at_ms=0))
    banner.announce_end(GameEnded(winner="w", at_ms=100))
    assert banner.text_at(100) == "WHITE WINS"


def test_subscribe_banner_wires_both_events():
    bus = EventBus()
    banner = subscribe_banner(bus, settings)
    bus.publish(GameStarted(at_ms=0))
    assert banner.text_at(0) == settings.START_BANNER_TEXT
    bus.publish(GameEnded(winner="w", at_ms=50))
    assert banner.text_at(50) == "WHITE WINS"
