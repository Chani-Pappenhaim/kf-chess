from config import settings
from client.home import RANDOM_COLOR, ButtonMenu, color_menu, home_menu, requested_color


def _button_centers(count):
    """Where the centre of each of a `count`-button menu's buttons lands,
    worked out independently of client/home.py."""
    bw, bh, gap = (
        settings.HOME_BUTTON_WIDTH, settings.HOME_BUTTON_HEIGHT, settings.HOME_BUTTON_GAP
    )
    x = settings.WINDOW_WIDTH // 2 - bw // 2 + bw // 2
    top = settings.WINDOW_HEIGHT // 2 - (count * bh + (count - 1) * gap) // 2
    return [(x, top + i * (bh + gap) + bh // 2) for i in range(count)]


def test_the_home_screen_offers_play_room_and_computer_top_to_bottom():
    home = home_menu(settings)
    assert [home.button_at(*c) for c in _button_centers(3)] == ["play", "room", "computer"]


def test_the_colour_screen_offers_white_black_and_random_top_to_bottom():
    colors = color_menu(settings)
    assert [colors.button_at(*c) for c in _button_centers(3)] == ["w", "b", RANDOM_COLOR]


def test_a_click_on_no_button_returns_nothing():
    assert home_menu(settings).button_at(0, 0) is None


def test_a_click_in_the_gap_between_buttons_returns_nothing():
    first, second = _button_centers(2)
    menu = ButtonMenu(settings, (("a", "A"), ("b", "B")))
    assert menu.button_at(first[0], (first[1] + second[1]) // 2) is None


def test_a_click_on_a_buttons_edge_counts_and_one_past_it_does_not():
    menu = ButtonMenu(settings, (("only", "Only"),))
    (x, y), = _button_centers(1)
    top = y - settings.HOME_BUTTON_HEIGHT // 2
    assert menu.button_at(x, top) == "only"
    assert menu.button_at(x, top - 1) is None


def test_random_asks_the_server_to_pick_and_a_colour_is_sent_as_is():
    assert requested_color(RANDOM_COLOR) == ""
    assert requested_color("w") == "w"


def test_both_screens_render_without_error():
    assert home_menu(settings).canvas() is not None
    assert color_menu(settings).canvas() is not None
