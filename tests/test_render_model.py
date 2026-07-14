import play
from config import settings
from view.render_model import RenderModel


def test_render_model_lists_every_piece_as_idle():
    engine = play.build_engine(settings)
    model = engine.render_model()
    assert isinstance(model, RenderModel)
    assert (model.width, model.height) == (8, 8)
    assert len(model.pieces) == 32  # standard chess starting position
    assert all(piece.state == "idle" for piece in model.pieces)
    assert not model.game_over


def test_render_model_places_a_known_piece():
    model = play.build_engine(settings).render_model()
    kings = [piece for piece in model.pieces if piece.token == "wK"]
    assert len(kings) == 1
    assert kings[0].cell == (7, 4)
