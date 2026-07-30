from server.allocator import GameAllocator


def test_a_single_server_gets_every_key():
    allocator = GameAllocator(["a"])
    assert allocator.for_key("x") == "a"
    assert allocator.for_key("y") == "a"


def test_the_same_key_always_lands_on_the_same_server():
    allocator = GameAllocator(["a", "b", "c"])
    assert allocator.for_key("dana") == allocator.for_key("dana")


def test_keys_spread_across_more_than_one_server():
    allocator = GameAllocator(["a", "b", "c"])
    picks = {allocator.for_key(f"key-{i}") for i in range(200)}
    assert len(picks) > 1


def test_adding_a_server_remaps_only_a_slice_of_keys():
    keys = [f"key-{i}" for i in range(1000)]
    before = GameAllocator(["a", "b", "c"])
    after = GameAllocator(["a", "b", "c", "d"])
    moved = sum(1 for key in keys if before.for_key(key) != after.for_key(key))
    # Plain mod-N hashing would remap nearly everything; a hash ring only
    # remaps the slice that now belongs to the new server (~1/4 here).
    assert 0 < moved < len(keys) * 0.4
