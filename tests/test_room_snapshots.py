from server.room_snapshots import InMemoryRoomSnapshots, RoomSnapshots


def test_it_satisfies_the_room_snapshots_contract():
    assert isinstance(InMemoryRoomSnapshots(), RoomSnapshots)


def test_a_saved_snapshot_is_loaded_back():
    snapshots = InMemoryRoomSnapshots()
    snapshots.save("room-1", {"pieces": []})
    assert snapshots.load("room-1") == {"pieces": []}


def test_an_unsaved_room_has_no_snapshot():
    assert InMemoryRoomSnapshots().load("nope") is None


def test_a_later_save_replaces_the_earlier_one():
    snapshots = InMemoryRoomSnapshots()
    snapshots.save("room-1", {"pieces": ["old"]})
    snapshots.save("room-1", {"pieces": ["new"]})
    assert snapshots.load("room-1") == {"pieces": ["new"]}


def test_deleting_a_snapshot_removes_it():
    snapshots = InMemoryRoomSnapshots()
    snapshots.save("room-1", {"pieces": []})
    snapshots.delete("room-1")
    assert snapshots.load("room-1") is None


def test_deleting_an_unsaved_room_is_a_no_op():
    InMemoryRoomSnapshots().delete("never-saved")  # must not raise
