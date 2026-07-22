import pytest

from protocol.errors import ProtocolError
from protocol.messages import (
    HintsReply,
    HintsRequest,
    JumpRequest,
    MoveRequest,
    StateUpdate,
    decode,
    encode,
)
from server.handler import CommandHandler
from view.render_model import RenderModel, RenderPiece

BOARD_HEIGHT = 8


class FakeEngine:
    """Records what it was asked to do and answers ownership from a fixed board,
    so the handler is tested without a real game."""

    def __init__(self, pieces, targets=()):
        # pieces: {cell: token}
        self.moves = []
        self.jumps = []
        self._pieces = pieces
        self._targets = targets

    def render_model(self):
        pieces = tuple(RenderPiece(token, cell) for cell, token in self._pieces.items())
        return RenderModel(pieces=pieces, width=8, height=BOARD_HEIGHT)

    def request_move(self, start, end):
        self.moves.append((start, end))

    def request_jump(self, cell):
        self.jumps.append(cell)

    def legal_targets(self, cell):
        return self._targets


def handler(color="w", pieces=None, targets=()):
    engine = FakeEngine({(6, 4): "wP"} if pieces is None else pieces, targets)
    sent = []
    return CommandHandler(engine, BOARD_HEIGHT, sent.append, color), engine, sent


def test_a_move_of_your_own_piece_reaches_the_engine():
    command, engine, _ = handler(color="w", pieces={(6, 4): "wP"})
    command.handle(encode(MoveRequest("WPe2e4")))
    assert engine.moves == [((6, 4), (4, 4))]


def test_a_move_of_the_other_colour_is_ignored():
    # The guard: a white session cannot move a black piece, whatever it claims.
    command, engine, _ = handler(color="w", pieces={(6, 4): "bP"})
    command.handle(encode(MoveRequest("BPe2e4")))
    assert engine.moves == []


def test_a_move_from_an_empty_square_is_ignored():
    command, engine, _ = handler(color="w", pieces={})
    command.handle(encode(MoveRequest("WPe2e4")))
    assert engine.moves == []


def test_the_piece_a_client_claims_is_ignored_only_the_square_counts():
    # The command says a black king; the board holds the session's own pawn, so
    # that is what moves. Claiming a piece cannot move one that is not there.
    command, engine, _ = handler(color="w", pieces={(6, 4): "wP"})
    command.handle(encode(MoveRequest("BKe2e4")))
    assert engine.moves == [((6, 4), (4, 4))]


def test_a_jump_of_your_own_piece_reaches_the_engine():
    command, engine, _ = handler(color="w", pieces={(7, 6): "wN"})
    command.handle(encode(JumpRequest("g1")))
    assert engine.jumps == [(7, 6)]


def test_a_jump_of_the_other_colour_is_ignored():
    command, engine, _ = handler(color="w", pieces={(7, 6): "bN"})
    command.handle(encode(JumpRequest("g1")))
    assert engine.jumps == []


def test_hints_are_answered_for_your_own_piece():
    command, _, sent = handler(color="w", pieces={(6, 4): "wP"}, targets=((5, 4), (4, 4)))
    command.handle(encode(HintsRequest("e2")))
    assert decode(sent[0]) == HintsReply("e2", ("e3", "e4"))


def test_hints_for_the_other_colour_reveal_nothing():
    command, _, sent = handler(color="w", pieces={(6, 4): "bP"}, targets=((5, 4),))
    command.handle(encode(HintsRequest("e2")))
    assert decode(sent[0]) == HintsReply("e2", ())


def test_commands_do_not_reply_only_hints_do():
    command, _, sent = handler(color="w", pieces={(6, 4): "wP", (7, 6): "wN"})
    command.handle(encode(MoveRequest("WPe2e4")))
    command.handle(encode(JumpRequest("g1")))
    assert sent == []


def test_a_message_only_a_server_sends_is_refused():
    command, engine, _ = handler()
    with pytest.raises(ProtocolError):
        command.handle(encode(StateUpdate({"pieces": []})))
    assert engine.moves == []


def test_text_that_is_not_a_message_is_refused():
    command, _, _ = handler()
    with pytest.raises(ProtocolError):
        command.handle("nonsense")


def test_a_move_command_that_cannot_be_read_is_refused():
    command, engine, _ = handler()
    with pytest.raises(ProtocolError):
        command.handle(encode(MoveRequest("WPe2")))
    assert engine.moves == []


def test_a_session_holds_the_colour_it_was_given():
    command, _, _ = handler(color="b")
    assert command.color == "b"
