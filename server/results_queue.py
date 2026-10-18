"""A durable queue for finished-game results, so recording one never blocks
the room that produced it and never loses a result to a DB that is briefly
unreachable.

`subscribe_ratings`/`subscribe_history` used to write to the account/history
store directly, in-line, inside the event that fires when a game ends - a
blocking DB call on the same thread that runs every room's clock (see
`server/results_worker.py` for where the write actually happens now). This
queue is the seam that decouples "a game ended" from "the result is durably
written": publishing is fast and in-process; a separate worker drains it and
retries until the write lands.
"""
from __future__ import annotations

import json
from typing import Protocol, runtime_checkable

_TOPIC = "game-results"


@runtime_checkable
class ResultsQueue(Protocol):
    def publish(self, payload: dict) -> None:
        ...

    def consume(self) -> list:
        ...

    def commit(self) -> None:
        ...


class InMemoryResultsQueue:
    """Fan-out-free work queue: each `consume()` drains what is pending, so
    (unlike PubSub's fan-out) two consumers sharing a broker split the work
    instead of each seeing every message - matching a real queue's delivery
    to one worker, not every worker."""

    def __init__(self, broker=None):
        self._broker = broker if broker is not None else []

    def publish(self, payload):
        self._broker.append(payload)

    def consume(self):
        pending, self._broker[:] = list(self._broker), []
        return pending

    def commit(self):
        """A no-op: `consume()` already removed the batch from the broker the
        moment it was read, so there is no separate offset to advance -
        unlike Kafka, there is nothing left to lose by not calling this.
        Exists so `server/results_worker.py::process_batch` can call
        `queue.commit()` unconditionally regardless of which queue it holds."""


class KafkaResultsQueue:  # pragma: no cover - kafka shell, exercised by running it
    def __init__(self, url):
        from kafka import KafkaConsumer, KafkaProducer

        self._producer = KafkaProducer(
            bootstrap_servers=url,
            value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
        )
        self._consumer = KafkaConsumer(
            _TOPIC,
            bootstrap_servers=url,
            value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
            enable_auto_commit=False,  # commit only after a write actually succeeds
            auto_offset_reset="earliest",
            consumer_timeout_ms=0,
        )

    def publish(self, payload):
        self._producer.send(_TOPIC, payload)
        self._producer.flush()

    def consume(self):
        """One poll's worth of pending results. The caller is responsible for
        calling `commit()` only once every result in the batch is durably
        written - that is what makes a crash mid-write safe to retry."""
        records = self._consumer.poll(timeout_ms=1000)
        return [record.value for batch in records.values() for record in batch]

    def commit(self):  # pragma: no cover
        self._consumer.commit()
