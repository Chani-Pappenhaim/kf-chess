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

BOARD_HEIGHT = 8


class FakeEngine:
    """Records what it was asked to do, so a test can check the handler drives
    the engine correctly without running a real game."""

    def __init__(self, targets=()):
        self.moves = []
        self.jumps = []
        self._targets = targets

    def request_move(self, start, end):
        self.moves.append((start, end))

    def request_jump(self, cell):
        self.jumps.append(cell)

    def legal_targets(self, cell):
        return self._targets


def handler(targets=()):
    """A handler over a fake engine, and the lines it has replied with."""
    engine, sent = FakeEngine(targets), []
    return CommandHandler(engine, BOARD_HEIGHT, sent.append), engine, sent


def test_a_move_request_reaches_the_engine_as_two_cells():
    command, engine, _ = handler()
    command.handle(encode(MoveRequest("WQe2e5")))
    assert engine.moves == [((6, 4), (3, 4))]


def test_a_jump_request_reaches_the_engine_as_one_cell():
    command, engine, _ = handler()
    command.handle(encode(JumpRequest("e4")))
    assert engine.jumps == [(4, 4)]


def test_the_piece_a_client_claims_to_move_is_ignored():
    # The command says a white queen; the engine is told only which squares.
    # Whatever the board actually holds on e2 is what moves, so a client cannot
    # move a piece that is not there by naming it.
    command, engine, _ = handler()
    command.handle(encode(MoveRequest("BKe2e5")))
    assert engine.moves == [((6, 4), (3, 4))]


def test_a_hints_request_is_answered_in_squares():
    command, _, sent = handler(targets=((5, 4), (4, 4)))
    command.handle(encode(HintsRequest("e2")))

    assert len(sent) == 1
    reply = decode(sent[0])
    assert reply == HintsReply("e2", ("e3", "e4"))


def test_a_piece_with_nowhere_to_go_is_answered_with_nothing():
    command, _, sent = handler(targets=())
    command.handle(encode(HintsRequest("e2")))
    assert decode(sent[0]) == HintsReply("e2", ())


def test_only_a_hints_request_gets_a_reply():
    # Moves and jumps are told, not asked: what they did shows up in the next
    # state the server sends out.
    command, _, sent = handler()
    command.handle(encode(MoveRequest("WQe2e5")))
    command.handle(encode(JumpRequest("e4")))
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
        command.handle(encode(MoveRequest("WQe2")))
    assert engine.moves == []
