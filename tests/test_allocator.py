from server.allocator import GameAllocator, mint_room_id, parse_pool


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


def test_a_single_server_parses_to_one_entry():
    assert parse_pool("local=ws://localhost:8765") == {"local": "ws://localhost:8765"}


def test_several_servers_parse_to_several_entries():
    assert parse_pool("a=ws://host-a:8765,b=ws://host-b:8765") == {
        "a": "ws://host-a:8765",
        "b": "ws://host-b:8765",
    }


def test_minted_room_ids_are_short_and_distinct():
    a, b = mint_room_id(), mint_room_id()
    assert a != b
    assert len(a) < 12
