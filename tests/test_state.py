import json

import play
from config import settings
from game.move_log import MoveRecord
from protocol.state import decode_model, encode_model
from view.render_model import MOVE_STATE, RenderModel, RenderPiece


def moving_game():
    """A game caught mid-move, so the state carries every field that varies."""
    engine = play.build_engine(settings)
    engine.request_move((6, 0), (4, 0))
    engine.wait(settings.MOVE_DURATION // 2)
    return engine.render_model()


def test_a_state_survives_the_round_trip_unchanged():
    model = moving_game()
    assert decode_model(encode_model(model)) == model


def test_the_encoded_state_is_plain_json():
    # Nothing but built-ins may cross: the next layer only has json to work with.
    json.dumps(encode_model(moving_game()))


def test_a_move_history_limit_keeps_only_the_trailing_records():
    model = RenderModel(
        pieces=(), width=8, height=8,
        moves=tuple(MoveRecord("w", f"e2e{i}", i) for i in range(5)),
    )
    encoded = encode_model(model, move_history_limit=2)
    assert [m["notation"] for m in encoded["moves"]] == ["e2e3", "e2e4"]


def test_no_limit_keeps_the_whole_move_history():
    model = RenderModel(
        pieces=(), width=8, height=8,
        moves=tuple(MoveRecord("w", f"e2e{i}", i) for i in range(5)),
    )
    assert len(encode_model(model)["moves"]) == 5


def test_cells_come_back_as_tuples():
    # A list would compare unequal to every cell in the rest of the code, and
    # could not be used as a key at all.
    piece = decode_model(encode_model(moving_game())).pieces[0]
    assert isinstance(piece.cell, tuple)


def test_a_piece_in_flight_keeps_its_target():
    model = moving_game()
    mover = decode_model(encode_model(model)).piece_at((6, 0))
    assert mover.state == MOVE_STATE
    assert mover.target == (5, 0)
    assert 0 < mover.progress < 1


def test_a_still_piece_has_no_target_on_either_side():
    model = RenderModel(pieces=(RenderPiece("wK", (7, 4)),), width=8, height=8)
    assert encode_model(model)["pieces"][0]["target"] is None
    assert decode_model(encode_model(model)).pieces[0].target is None


def test_the_move_log_and_scores_cross_too():
    model = RenderModel(
        pieces=(),
        width=8,
        height=8,
        moves=(MoveRecord("w", "e2-e4", 4105),),
        scores={"w": 5, "b": 3},
    )
    restored = decode_model(encode_model(model))
    assert restored.moves == (MoveRecord("w", "e2-e4", 4105),)
    assert restored.scores == {"w": 5, "b": 3}


def test_a_finished_game_crosses_as_finished():
    model = RenderModel(pieces=(), width=8, height=8, game_over=True, clock=9000)
    restored = decode_model(encode_model(model))
    assert restored.game_over is True
    assert restored.clock == 9000


def test_player_names_cross_with_the_state():
    model = RenderModel(pieces=(), width=8, height=8, players={"w": "dana", "b": "yossi"})
    assert decode_model(encode_model(model)).players == {"w": "dana", "b": "yossi"}


def test_player_ratings_cross_with_the_state():
    model = RenderModel(pieces=(), width=8, height=8, ratings={"w": 1516, "b": 1484})
    assert decode_model(encode_model(model)).ratings == {"w": 1516, "b": 1484}


def test_the_viewers_cross_with_the_state():
    model = RenderModel(pieces=(), width=8, height=8, viewers=("chani", "avi"))
    assert decode_model(encode_model(model)).viewers == ("chani", "avi")


def test_a_disconnect_countdown_crosses_with_the_state():
    model = RenderModel(pieces=(), width=8, height=8, countdown=12)
    assert decode_model(encode_model(model)).countdown == 12
