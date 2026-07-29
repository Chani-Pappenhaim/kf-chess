import play
from client.gateway import NetworkGateway
from client.inbox import Inbox
from config import settings
from gateway.gateway import GameGateway
from protocol.messages import HintsRequest, JumpRequest, MoveRequest, decode


def connected():
    """A gateway over an inbox that has already received one state, and the
    lines it has sent to the server."""
    inbox, sent = Inbox(), []
    inbox.receive_state(play.build_engine(settings).render_model())
    return NetworkGateway(inbox, sent.append), inbox, sent


def test_it_satisfies_the_same_contract_as_the_engine():
    gateway, _inbox, _sent = connected()
    assert isinstance(gateway, GameGateway)


def test_the_model_to_draw_is_the_last_state_received():
    gateway, inbox, _sent = connected()
    assert gateway.render_model() is inbox.model()


def test_a_move_goes_out_naming_the_piece_that_is_there():
    gateway, _inbox, sent = connected()
    gateway.request_move((6, 4), (4, 4))     # white pawn e2 -> e4
    assert decode(sent[0]) == MoveRequest("WPe2e4")


def test_a_move_from_an_empty_square_is_not_sent():
    # The selection can outlive the piece; there is nothing to name, and
    # nothing the server could move.
    gateway, _inbox, sent = connected()
    gateway.request_move((4, 4), (3, 4))
    assert sent == []


def test_a_jump_goes_out_as_the_square_it_is_on():
    gateway, _inbox, sent = connected()
    gateway.request_jump((7, 6))             # white knight g1
    assert decode(sent[0]) == JumpRequest("g1")


def test_asking_for_hints_sends_one_request_and_draws_none_yet():
    gateway, _inbox, sent = connected()
    assert gateway.legal_targets((6, 4)) == ()
    assert decode(sent[0]) == HintsRequest("e2")


def test_the_same_square_is_asked_about_only_once():
    # legal_targets is read every frame. One message per selection, not sixty
    # per second.
    gateway, _inbox, sent = connected()
    for _frame in range(60):
        gateway.legal_targets((6, 4))
    assert len(sent) == 1


def test_an_answer_is_turned_back_into_cells():
    gateway, inbox, _sent = connected()
    gateway.legal_targets((6, 4))            # asks
    inbox.receive_hints("e2", ("e3", "e4"))  # the server answers

    assert gateway.legal_targets((6, 4)) == ((5, 4), (4, 4))


def test_an_answered_square_is_never_asked_about_again():
    gateway, inbox, sent = connected()
    gateway.legal_targets((6, 4))
    inbox.receive_hints("e2", ("e3",))
    for _frame in range(60):
        gateway.legal_targets((6, 4))
    assert len(sent) == 1


def test_choosing_another_piece_asks_about_that_one():
    gateway, _inbox, sent = connected()
    gateway.legal_targets((6, 4))            # e2
    gateway.legal_targets((7, 6))            # g1
    assert [decode(line).square for line in sent] == ["e2", "g1"]
