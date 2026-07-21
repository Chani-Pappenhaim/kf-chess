from client.inbox import Inbox
from view.render_model import RenderModel


def a_model(clock=0):
    return RenderModel(pieces=(), width=8, height=8, clock=clock)


def test_nothing_has_arrived_before_the_first_state():
    assert Inbox().model() is None


def test_the_last_state_is_what_is_read():
    # No history is kept: a client draws the newest state and nothing else.
    inbox = Inbox()
    inbox.receive_state(a_model(clock=100))
    inbox.receive_state(a_model(clock=200))
    assert inbox.model().clock == 200


def test_hints_are_unknown_until_they_are_told():
    assert Inbox().hints("e2") is None


def test_hints_are_returned_for_the_square_they_were_given_for():
    inbox = Inbox()
    inbox.receive_hints("e2", ("e3", "e4"))
    assert inbox.hints("e2") == ("e3", "e4")


def test_hints_for_one_square_are_not_an_answer_about_another():
    inbox = Inbox()
    inbox.receive_hints("e2", ("e3", "e4"))
    assert inbox.hints("g1") is None


def test_a_piece_with_nowhere_to_go_is_an_answer_not_a_silence():
    # An empty tuple means "told: nowhere"; None means "not told yet". The
    # difference is what stops the gateway asking the same thing forever.
    inbox = Inbox()
    inbox.receive_hints("e2", ())
    assert inbox.hints("e2") == ()
    assert inbox.hints("e2") is not None
