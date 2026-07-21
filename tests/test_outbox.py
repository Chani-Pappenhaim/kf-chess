from server.outbox import Outbox


def test_a_line_for_everyone_has_no_addressee():
    outbox = Outbox()
    outbox.to_all("hello")
    assert outbox.drain() == [(None, "hello")]


def test_a_line_for_one_client_is_addressed_to_it():
    outbox = Outbox()
    outbox.to("a client", "your hints")
    assert outbox.drain() == [("a client", "your hints")]


def test_lines_come_out_in_the_order_they_went_in():
    outbox = Outbox()
    outbox.to_all("first")
    outbox.to("a client", "second")
    outbox.to_all("third")
    assert [line for _target, line in outbox.drain()] == ["first", "second", "third"]


def test_draining_empties_the_outbox():
    outbox = Outbox()
    outbox.to_all("once")
    outbox.drain()
    assert outbox.drain() == []


def test_a_line_queued_after_a_drain_waits_for_the_next_one():
    # The drain takes a snapshot: what the game says while a batch is being
    # sent goes out with the batch after it, never extending this one.
    outbox = Outbox()
    outbox.to_all("first")
    batch = outbox.drain()
    outbox.to_all("second")
    assert batch == [(None, "first")]
    assert outbox.drain() == [(None, "second")]


def test_an_untouched_outbox_has_nothing_to_send():
    assert Outbox().drain() == []
