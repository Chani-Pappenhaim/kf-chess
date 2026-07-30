from server.room_directory import InMemoryRoomDirectory


def test_an_unknown_room_has_no_host():
    assert InMemoryRoomDirectory().get("1") is None


def test_a_registered_room_is_found_by_its_host():
    directory = InMemoryRoomDirectory()
    directory.put("1", "server-a")
    assert directory.get("1") == "server-a"


def test_a_removed_room_has_no_host():
    directory = InMemoryRoomDirectory()
    directory.put("1", "server-a")
    directory.remove("1")
    assert directory.get("1") is None
