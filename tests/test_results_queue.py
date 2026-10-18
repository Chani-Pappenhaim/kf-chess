from server.results_queue import InMemoryResultsQueue


def test_an_empty_queue_has_nothing_pending():
    assert InMemoryResultsQueue().consume() == []


def test_consume_drains_everything_published():
    queue = InMemoryResultsQueue()
    queue.publish({"kind": "rating", "username": "dana", "rating": 1216})
    assert queue.consume() == [{"kind": "rating", "username": "dana", "rating": 1216}]
    assert queue.consume() == []


def test_results_come_out_in_publish_order():
    queue = InMemoryResultsQueue()
    queue.publish({"kind": "rating", "username": "a", "rating": 1})
    queue.publish({"kind": "rating", "username": "b", "rating": 2})
    assert [entry["username"] for entry in queue.consume()] == ["a", "b"]


def test_two_workers_sharing_a_broker_split_the_work_instead_of_each_seeing_it():
    # Unlike PubSub's fan-out, a results queue is a work queue: once one
    # worker consumes a message, it is gone for the other.
    broker = []
    one, two = InMemoryResultsQueue(broker), InMemoryResultsQueue(broker)
    one.publish({"kind": "rating", "username": "dana", "rating": 1216})
    assert one.consume() == [{"kind": "rating", "username": "dana", "rating": 1216}]
    assert two.consume() == []
