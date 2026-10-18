from dataclasses import FrozenInstanceError

import pytest

from bot.position import capture
from tests.support import engine_with

KINGS = [("wK", (7, 4)), ("bK", (0, 4))]


def test_a_position_lists_the_legal_moves_of_each_of_its_colours_pieces():
    position = capture(engine_with(KINGS + [("wR", (7, 0))]), "w")
    assert set(position.moves) == {(7, 0), (7, 4)}
    assert (0, 0) in position.moves[(7, 0)]


def test_the_other_colours_pieces_are_seen_but_not_moved():
    position = capture(engine_with(KINGS + [("bQ", (0, 0))]), "w")
    assert (0, 0) not in position.moves
    assert position.occupants[(0, 0)] == "bQ"


def test_a_busy_piece_offers_no_moves_and_is_listed_as_busy():
    engine = engine_with(KINGS + [("wR", (7, 0))])
    engine.request_move((7, 0), (3, 0))
    position = capture(engine, "w")
    assert (7, 0) not in position.moves
    assert position.busy == (("wR", (7, 0), "move"),)


def test_a_move_is_legal_only_if_it_was_on_the_list():
    position = capture(engine_with(KINGS + [("wR", (7, 0))]), "w")
    assert position.is_legal((7, 0), (0, 0))
    assert not position.is_legal((7, 0), (6, 1))
    assert not position.is_legal((5, 5), (4, 5))


def test_captured_by_names_only_an_enemy_piece():
    position = capture(engine_with(KINGS + [("wR", (7, 0)), ("bN", (0, 0))]), "w")
    assert position.captured_by((0, 0)) == "bN"
    assert position.captured_by((7, 4)) is None   # own piece
    assert position.captured_by((3, 3)) is None   # empty


def test_a_position_is_frozen():
    position = capture(engine_with(KINGS), "w")
    with pytest.raises(FrozenInstanceError):
        position.color = "b"
