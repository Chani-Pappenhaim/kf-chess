"""Fast, fire-and-forget messaging between Game Servers, as a contract - poll-
based so a consumer drains it from its own tick, with no thread of its own.
"""
from __future__ import annotations

import json
from typing import Protocol, runtime_checkable


@runtime_checkable
class PubSub(Protocol):
    def publish(self, channel, payload) -> None:
        ...

    def poll(self, channel) -> list:
        ...


class InMemoryPubSub:
    """Fan-out, not a work queue: each instance is an independent subscriber
    over a shared, append-only log, seeing only what is published after it
    starts polling a channel - a new subscriber gets no history, same as
    Redis. Share one `broker` dict between instances to simulate several
    processes listening to the same channel."""

    def __init__(self, broker=None):
        self._broker = broker if broker is not None else {}
        # A late joiner starts past whatever is already in the broker, so it
        # sees no history - same as Redis, whose subscription starts from now.
        self._seen = {channel: len(messages) for channel, messages in self._broker.items()}

    def publish(self, channel, payload):
        self._broker.setdefault(channel, []).append(payload)

    def poll(self, channel):
        published = self._broker.get(channel, [])
        seen = self._seen.get(channel, 0)
        self._seen[channel] = len(published)
        return published[seen:]


class RedisPubSub:  # pragma: no cover - redis shell, exercised by running it
    def __init__(self, url):
        import redis

        self._redis = redis.Redis.from_url(url, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        self._subscribed = set()

    def publish(self, channel, payload):
        self._redis.publish(channel, json.dumps(payload))

    def poll(self, channel):
        if channel not in self._subscribed:
            self._pubsub.subscribe(channel)
            self._subscribed.add(channel)
        pending = []
        while True:
            message = self._pubsub.get_message(timeout=0)
            if message is None:
                return pending
            if message["type"] == "message":
                pending.append(json.loads(message["data"]))
