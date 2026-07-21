"""EventBus - delivers each published event to whoever subscribed to its type.

Knows nothing about chess: it routes by type and calls callables, so the same
bus can carry any other kind of event.
"""
from __future__ import annotations


class EventBus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type, handler):
        """Call `handler(event)` for every event of exactly `event_type`.
        Matching is by exact type, never by subclass."""
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event):
        """Hand `event` to its subscribers, in the order they subscribed.

        A handler that raises is left to raise; a subscriber that must not break
        the publisher contains its own failures, so the bus stays free of policy.
        """
        for handler in self._subscribers.get(type(event), ()):
            handler(event)
