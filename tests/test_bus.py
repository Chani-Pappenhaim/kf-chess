from dataclasses import dataclass

import pytest

from events.bus import EventBus


@dataclass(frozen=True)
class Alpha:
    value: int = 1


@dataclass(frozen=True)
class Beta:
    value: int = 2


def collector():
    """A subscriber that only records what it was handed."""
    seen = []
    return seen, seen.append


def test_a_subscriber_receives_the_event_it_asked_for():
    bus = EventBus()
    seen, handler = collector()
    bus.subscribe(Alpha, handler)
    event = Alpha()
    bus.publish(event)
    assert seen == [event]


def test_a_subscriber_never_sees_another_type():
    # The routing table is what spares each subscriber a type check of its own.
    bus = EventBus()
    seen, handler = collector()
    bus.subscribe(Alpha, handler)
    bus.publish(Beta())
    assert seen == []


def test_every_subscriber_of_a_type_is_called_in_subscription_order():
    bus = EventBus()
    order = []
    bus.subscribe(Alpha, lambda event: order.append("first"))
    bus.subscribe(Alpha, lambda event: order.append("second"))
    bus.publish(Alpha())
    assert order == ["first", "second"]


def test_one_subscriber_may_take_several_types():
    bus = EventBus()
    seen, handler = collector()
    bus.subscribe(Alpha, handler)
    bus.subscribe(Beta, handler)
    bus.publish(Alpha())
    bus.publish(Beta())
    assert seen == [Alpha(), Beta()]


def test_publishing_with_nobody_listening_is_silent():
    EventBus().publish(Alpha())


def test_a_raising_subscriber_is_not_contained():
    bus = EventBus()

    def broken(event):
        raise ValueError("subscriber is broken")

    bus.subscribe(Alpha, broken)
    with pytest.raises(ValueError):
        bus.publish(Alpha())
