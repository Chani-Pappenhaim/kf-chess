from config import settings
from board.board import Board
from events.bus import EventBus
from rules.rule_registry import build_default_registry
from game.composition import build_game


def make_controller(rows):
    # The controller is exercised over the real graph, so this asks the
    # composition root for it rather than repeating the wiring here.
    board = Board(rows, ".")
    registry = build_default_registry(settings)
    engine, controller = build_game(board, registry, settings, EventBus())
    return controller, engine, board


def cell_to_pixel(row, col):
    return col * settings.CELL_SIZE, row * settings.CELL_SIZE


def test_first_click_selects_own_piece():
    controller, engine, board = make_controller([["wK", "."], [".", "."]])
    controller.click(*cell_to_pixel(0, 0))
    assert controller.selected == (0, 0)


def test_first_click_on_empty_cell_selects_nothing():
    controller, engine, board = make_controller([["wK", "."], [".", "."]])
    controller.click(*cell_to_pixel(1, 1))
    assert controller.selected is None


def test_legal_targets_is_empty_when_nothing_is_selected():
    controller, engine, board = make_controller([["wR", ".", "."], [".", ".", "."], [".", ".", "."]])
    assert controller.legal_targets == ()


def test_legal_targets_reflects_the_selected_piece():
    controller, engine, board = make_controller([["wR", ".", "."], [".", ".", "."], [".", ".", "."]])
    controller.click(*cell_to_pixel(0, 0))  # select the rook
    assert set(controller.legal_targets) == {(0, 1), (0, 2), (1, 0), (2, 0)}


def test_click_outside_board_with_no_selection_is_ignored():
    controller, engine, board = make_controller([["wK", "."], [".", "."]])
    controller.click(-10, -10)
    assert controller.selected is None


def test_click_outside_board_keeps_existing_selection():
    # Faithful to current behaviour: an outside-board click is a no-op and does
    # NOT cancel an existing selection.
    controller, engine, board = make_controller([["wK", "."], [".", "."]])
    controller.click(*cell_to_pixel(0, 0))
    controller.click(-10, -10)
    assert controller.selected == (0, 0)


def test_second_click_starts_move_and_clears_selection():
    controller, engine, board = make_controller([["wR", ".", "."], [".", ".", "."], [".", ".", "."]])
    controller.click(*cell_to_pixel(0, 0))
    controller.click(*cell_to_pixel(0, 2))
    assert controller.selected is None
    assert board.get(0, 0) == "wR"  # still at source until it arrives


def test_illegal_second_click_clears_selection():
    # Clicking an illegal destination cancels the selection (the target was
    # not a legal move), leaving the piece in place.
    controller, engine, board = make_controller([["wN", ".", "."], [".", ".", "."], [".", ".", "."]])
    controller.click(*cell_to_pixel(0, 0))
    controller.click(*cell_to_pixel(0, 1))  # not a legal knight move
    assert controller.selected is None
    assert board.get(0, 0) == "wN"


def test_clicking_another_friendly_piece_reselects():
    controller, engine, board = make_controller([["wR", ".", "wK"], [".", ".", "."]])
    controller.click(*cell_to_pixel(0, 0))
    controller.click(*cell_to_pixel(0, 2))  # friendly -> reselect
    assert controller.selected == (0, 2)


def test_jump_clears_selection():
    controller, engine, board = make_controller([["wK", "bR"], [".", "."]])
    controller.click(*cell_to_pixel(0, 0))
    controller.jump(*cell_to_pixel(0, 0))
    assert controller.selected is None


def test_jump_outside_board_is_ignored():
    controller, engine, board = make_controller([["wK", "."], [".", "."]])
    controller.jump(-10, -10)  # out of bounds: no crash, no selection
    assert controller.selected is None


def test_second_click_clears_a_selection_whose_piece_has_left():
    # The game can move on without going through this controller - a command
    # already in flight, or another player's client - so the selected square
    # may hold nothing by the time the second click lands.
    controller, engine, board = make_controller(
        [["wR", ".", "."], [".", ".", "."], [".", ".", "."]]
    )
    controller.click(*cell_to_pixel(0, 0))
    assert controller.selected == (0, 0)

    engine.request_move((0, 0), (0, 2))     # started behind the controller's back
    engine.wait(settings.MOVE_DURATION)     # the rook has stepped off (0, 0)

    controller.click(*cell_to_pixel(2, 2))
    assert controller.selected is None
