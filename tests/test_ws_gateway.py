from protocol.messages import CreateRoom, JoinRoom, Rejected, RoomEntered, SeekGame, decode, encode
from server.allocator import GameAllocator
from server.ws_gateway import plan_route, room_missing


def test_join_room_hashes_the_room_it_names():
    allocator = GameAllocator(["a"])
    first = encode(JoinRoom("some-room"))
    target, line = plan_route(JoinRoom("some-room"), first, allocator)
    assert target == "a"
    assert line == first  # forwarded unchanged


def test_a_fresh_create_room_is_minted_an_id_and_hashed():
    allocator = GameAllocator(["a"])
    first = encode(CreateRoom())  # empty id: not yet routed
    target, line = plan_route(CreateRoom(), first, allocator)
    assert target == "a"
    routed = decode(line)
    assert isinstance(routed, CreateRoom)
    assert routed.room_id != ""  # a fresh id was minted


def test_an_already_routed_create_room_is_not_re_minted():
    allocator = GameAllocator(["a"])
    first = encode(CreateRoom("chosen"))
    target, line = plan_route(CreateRoom("chosen"), first, allocator)
    assert target is None  # nothing left to decide
    assert line == first


def test_seek_game_has_no_room_bound_target():
    allocator = GameAllocator(["a"])
    first = encode(SeekGame())
    target, line = plan_route(SeekGame(), first, allocator)
    assert target is None
    assert line == first


def test_a_no_such_room_rejection_is_recognised_as_room_missing():
    line = encode(Rejected("no room with that id"))
    assert room_missing(line, "no room with that id") is True


def test_a_different_rejection_reason_is_not_room_missing():
    line = encode(Rejected("the game already has two players"))
    assert room_missing(line, "no room with that id") is False


def test_a_non_rejection_reply_is_not_room_missing():
    line = encode(RoomEntered("w", "7", False))
    assert room_missing(line, "no room with that id") is False
