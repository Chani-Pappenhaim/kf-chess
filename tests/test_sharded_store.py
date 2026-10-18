import pytest

from accounts.sharded_store import ShardedAccountStore
from tests.support import FakeAccountStore


def test_a_username_always_routes_to_the_same_shard():
    store = ShardedAccountStore([FakeAccountStore(), FakeAccountStore()])
    store.register("dana", "pw")
    first = store.authenticate("dana", "pw")
    # Registering again would fail loudly if routed to a different shard
    # (that shard has never heard of "dana"), so authenticate is enough proof.
    second = store.authenticate("dana", "pw")
    assert first == second is not None


def test_different_usernames_can_land_on_different_shards():
    shard_a, shard_b = FakeAccountStore(), FakeAccountStore()
    store = ShardedAccountStore([shard_a, shard_b])
    # Not every pair of names is guaranteed to split, but across enough of
    # them at least one should land on each shard - if not, the routing is
    # constant and the sharding is doing nothing.
    names = ("alice", "bob", "carol", "dave", "erin", "frank")
    for name in names:
        store.register(name, "pw")
    seen_on_a = any(shard_a.exists(name) for name in names)
    seen_on_b = any(shard_b.exists(name) for name in names)
    assert seen_on_a and seen_on_b


def test_exists_and_set_rating_route_to_the_shard_that_holds_the_account():
    store = ShardedAccountStore([FakeAccountStore(), FakeAccountStore()])
    store.register("dana", "pw")
    assert store.exists("dana")
    store.set_rating("dana", 1300)
    assert store.authenticate("dana", "pw").rating == 1300


def test_a_username_with_no_account_anywhere_does_not_exist():
    store = ShardedAccountStore([FakeAccountStore(), FakeAccountStore()])
    assert not store.exists("nobody")
    assert store.authenticate("nobody", "pw") is None


def test_at_least_one_shard_is_required():
    with pytest.raises(ValueError):
        ShardedAccountStore([])
