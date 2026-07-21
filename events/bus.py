"""EventBus - delivers each published event to whoever subscribed to its type.

Deliberately knows nothing about chess: it routes by type and calls callables,
so the same mechanism carries game events here and network events later.

The routing table is what replaces the type check a subscriber would otherwise
do on every event. A subscriber is any callable taking the event - it inherits
nothing and asks the event nothing - so it never learns the vocabulary of events
it did not ask for.
"""
from __future__ import annotations


class EventBus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type, handler):
        """Call `handler(event)` for every event published of exactly
        `event_type`. Matching is by exact type, not by subclass: an event is
        delivered on the strength of what it is, never of what it inherits."""
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event):
        """Hand `event` to its subscribers, in the order they subscribed.

        A handler that raises is left to raise: a broken subscriber is a bug to
        surface, not a condition to swallow. Where a subscriber must not be able
        to break the publisher - a remote client dropping its connection - the
        containment belongs to that subscriber, so the bus stays free of policy.
        """
        for handler in self._subscribers.get(type(event), ()):
            handler(event)
