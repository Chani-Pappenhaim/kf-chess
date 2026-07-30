from server.pubsub import InMemoryPubSub


def test_an_unpublished_channel_has_nothing_pending():
    assert InMemoryPubSub().poll("channel") == []


def test_a_published_message_is_polled_once():
    bus = InMemoryPubSub()
    bus.publish("channel", {"a": 1})
    assert bus.poll("channel") == [{"a": 1}]
    assert bus.poll("channel") == []


def test_messages_are_polled_in_publish_order():
    bus = InMemoryPubSub()
    bus.publish("channel", 1)
    bus.publish("channel", 2)
    assert bus.poll("channel") == [1, 2]


def test_channels_are_independent():
    bus = InMemoryPubSub()
    bus.publish("a", 1)
    assert bus.poll("b") == []
    assert bus.poll("a") == [1]


def test_two_subscribers_sharing_a_broker_each_see_every_message():
    # Fan-out, not a work queue: publishing once must not "use up" the
    # message for whichever subscriber polls first.
    broker = {}
    one, two = InMemoryPubSub(broker), InMemoryPubSub(broker)
    one.publish("channel", "hello")
    assert one.poll("channel") == ["hello"]
    assert two.poll("channel") == ["hello"]


def test_a_late_subscriber_sees_no_history():
    broker = {}
    early = InMemoryPubSub(broker)
    early.publish("channel", "before")
    late = InMemoryPubSub(broker)  # subscribes only from here on
    assert late.poll("channel") == []
    early.publish("channel", "after")
    assert late.poll("channel") == ["after"]
