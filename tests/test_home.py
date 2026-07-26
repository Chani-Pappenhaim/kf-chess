from config import settings
from client.home import HomeScreen


def _button_centers():
    width, height = settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT
    bw, bh, gap = (
        settings.HOME_BUTTON_WIDTH, settings.HOME_BUTTON_HEIGHT, settings.HOME_BUTTON_GAP
    )
    left = width // 2 - bw // 2
    top = height // 2 - (2 * bh + gap) // 2
    play = (left + bw // 2, top + bh // 2)
    room = (left + bw // 2, top + bh + gap + bh // 2)
    return play, room


def test_a_click_on_the_play_button_returns_play():
    play, _room = _button_centers()
    assert HomeScreen(settings).button_at(*play) == "play"


def test_a_click_on_the_room_button_returns_room():
    _play, room = _button_centers()
    assert HomeScreen(settings).button_at(*room) == "room"


def test_a_click_on_neither_button_returns_nothing():
    assert HomeScreen(settings).button_at(0, 0) is None


def test_the_home_screen_renders_both_buttons_without_error():
    # Draws the two labelled buttons onto a fresh canvas.
    assert HomeScreen(settings).canvas() is not None
