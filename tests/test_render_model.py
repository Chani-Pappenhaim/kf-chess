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


def test_render_model_starts_with_no_moves_and_zero_scores():
    model = play.build_engine(settings).render_model()
    assert model.moves == ()
    assert model.scores == {"w": 0, "b": 0}


def test_render_model_lists_a_completed_move():
    engine = play.build_engine(settings)
    engine.request_move((6, 0), (5, 0))   # white pawn a2 -> a3
    engine.wait(settings.MOVE_DURATION)
    model = engine.render_model()
    assert len(model.moves) == 1
    assert model.moves[0].color == "w"
    assert model.moves[0].notation == "a2-a3"


def test_render_model_marks_a_moving_piece_with_progress():
    engine = play.build_engine(settings)
    engine.request_move((6, 0), (5, 0))  # a one-step pawn move
    engine.wait(settings.MOVE_DURATION // 2)
    mover = [piece for piece in engine.render_model().pieces if piece.state == "move"]
    assert len(mover) == 1
    piece = mover[0]
    assert piece.cell == (6, 0)     # still on the square it is stepping off
    assert piece.target == (5, 0)   # sliding towards the next one
    assert 0 < piece.progress < 1


def test_render_model_marks_a_jumping_piece():
    engine = play.build_engine(settings)
    engine.request_jump((6, 0))
    jumper = [piece for piece in engine.render_model().pieces if piece.cell == (6, 0)]
    assert len(jumper) == 1
    assert jumper[0].state == "jump"


def test_render_model_reports_hop_progress_for_a_jumping_piece():
    engine = play.build_engine(settings)
    engine.request_jump((6, 0))
    engine.wait(settings.JUMP_DURATION // 2)  # mid-hop
    jumper = [piece for piece in engine.render_model().pieces if piece.cell == (6, 0)]
    assert len(jumper) == 1
    piece = jumper[0]
    assert piece.state == "jump"
    assert 0 < piece.progress < 1


def test_render_model_reports_cooldown_progress_for_a_resting_piece():
    engine = play.build_engine(settings)
    engine.request_move((6, 0), (5, 0))       # a one-step pawn move
    engine.wait(settings.MOVE_DURATION)        # arrives at (5, 0), long rest begins
    engine.wait(settings.LONG_REST_DURATION // 2)  # about halfway through the rest
    resting = [piece for piece in engine.render_model().pieces if piece.cell == (5, 0)]
    assert len(resting) == 1
    piece = resting[0]
    assert piece.state == "long_rest"
    assert 0 < piece.cooldown_progress < 1


def test_piece_at_finds_the_occupant_of_a_square():
    model = play.build_engine(settings).render_model()
    assert model.piece_at((7, 4)).token == "wK"


def test_piece_at_reports_an_empty_square_as_nothing_there():
    model = play.build_engine(settings).render_model()
    assert model.piece_at((4, 4)) is None
    assert model.selectable((4, 4)) is False
