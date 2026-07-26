import numpy as np

from config import settings
from ui.hud import Hud
from ui.animation import BannerAnimation
from view.render_model import RenderModel
from game.events import GameEnded
from game.move_log import MoveRecord


class _FakeCanvas:
    def __init__(self, width, height):
        self.img = np.zeros((height, width, 4), dtype=np.uint8)
        self.texts = []

    def put_text(self, txt, x, y, size, color, thickness):
        self.texts.append(txt)


def _canvas():
    return _FakeCanvas(settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)


class _NoBanner:
    """Stands in for the BannerAnimation where the banner is beside the point."""

    def text_at(self, clock):
        return None


def _hud(banner=None):
    return Hud(settings, banner or _NoBanner())


def _model(**overrides):
    base = dict(pieces=(), width=8, height=8)
    base.update(overrides)
    return RenderModel(**base)


def test_hud_shows_the_title_and_both_scores():
    canvas = _canvas()
    _hud().draw(canvas, _model(scores={"w": 5, "b": 3}))
    assert settings.WINDOW_TITLE in canvas.texts
    assert "Score: 5" in canvas.texts  # white, below the board
    assert "Score: 3" in canvas.texts  # black, above the board


def test_hud_shows_each_players_name_rating_and_score():
    canvas = _canvas()
    _hud().draw(canvas, _model(
        scores={"w": 5, "b": 3},
        players={"w": "dana", "b": "yossi"},
        ratings={"w": 1516, "b": 1484},
    ))
    assert "dana  Rating 1516  Score: 5" in canvas.texts    # white, below
    assert "yossi  Rating 1484  Score: 3" in canvas.texts   # black, above


def test_hud_marks_only_the_local_players_side():
    canvas = _canvas()
    hud = Hud(settings, _NoBanner(), own_color="w")
    hud.draw(canvas, _model(
        scores={"w": 5, "b": 3},
        players={"w": "dana", "b": "yossi"},
        ratings={"w": 1516, "b": 1484},
    ))
    joined = " | ".join(canvas.texts)
    assert f"dana  Rating 1516  Score: 5{settings.YOU_MARKER}" in canvas.texts
    assert f"yossi  Rating 1484  Score: 3{settings.YOU_MARKER}" not in joined


def test_hud_shows_the_name_alone_when_a_rating_is_missing():
    # A named player whose rating has not arrived yet: name, no parentheses.
    canvas = _canvas()
    _hud().draw(canvas, _model(scores={"w": 5}, players={"w": "dana"}))
    assert "dana  Score: 5" in canvas.texts


def test_hud_shows_a_bare_score_when_no_one_has_that_colour():
    # Local play, and any colour nobody has joined as yet: no name, just a score.
    canvas = _canvas()
    _hud().draw(canvas, _model(scores={"w": 0, "b": 0}))
    assert "Score: 0" in canvas.texts


def test_hud_shows_the_room_id_on_top():
    canvas = _canvas()
    Hud(settings, _NoBanner(), room_id="7").draw(canvas, _model())
    assert settings.ROOM_ID_LABEL.format(room_id="7") in canvas.texts


def test_hud_shows_the_disconnect_countdown_while_it_runs():
    canvas = _canvas()
    _hud().draw(canvas, _model(countdown=12))
    assert settings.DISCONNECT_NOTICE.format(seconds=12) in canvas.texts


def test_hud_lists_who_is_watching():
    canvas = _canvas()
    _hud().draw(canvas, _model(viewers=("chani", "avi")))
    assert settings.VIEWERS_LABEL.format(names="chani, avi") in canvas.texts


def test_hud_draws_coordinate_labels():
    canvas = _canvas()
    _hud().draw(canvas, _model())
    assert "a" in canvas.texts and "h" in canvas.texts
    assert "1" in canvas.texts and "8" in canvas.texts


def test_hud_lists_each_colors_moves_in_its_panel():
    moves = (MoveRecord("w", "e2-e4", 4105), MoveRecord("b", "e7-e5", 9000))
    canvas = _canvas()
    _hud().draw(canvas, _model(moves=moves))
    assert "e2-e4" in canvas.texts       # white panel
    assert "e7-e5" in canvas.texts       # black panel
    assert "00:04.105" in canvas.texts   # formatted move time


def test_hud_draws_whatever_the_animation_is_showing():
    banner = BannerAnimation(settings)
    banner.announce_end(GameEnded(winner="w", at_ms=0))
    canvas = _canvas()
    _hud(banner).draw(canvas, _model(clock=0))
    assert "WHITE WINS" in canvas.texts


def test_hud_draws_no_banner_when_the_animation_shows_none():
    canvas = _canvas()
    _hud().draw(canvas, _model(clock=0))
    assert canvas.texts and "WINS" not in " ".join(canvas.texts)
