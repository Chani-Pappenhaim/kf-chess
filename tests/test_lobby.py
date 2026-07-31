from server.lobby import Lobby


class FakeRoom:
    def __init__(self, room_id):
        self.id = room_id
        self.ticks = []
        self.is_empty = False

    def tick(self, dt):
        self.ticks.append(dt)


def lobby(server_id="test-server"):
    created = []

    def factory(room_id):
        room = FakeRoom(room_id)
        created.append(room)
        return room

    return Lobby(factory, server_id), created


def test_create_opens_a_room_with_a_fresh_id():
    hall, _ = lobby()
    assert hall.create().id != hall.create().id


def test_create_can_be_given_an_explicit_id():
    hall, _ = lobby()
    assert hall.create("chosen").id == "chosen"


def test_a_created_room_is_found_by_its_id():
    hall, _ = lobby()
    room = hall.create()
    assert hall.room(room.id) is room


def test_an_unknown_id_finds_no_room():
    hall, _ = lobby()
    assert hall.room("nope") is None


def test_get_or_create_opens_a_room_the_first_time():
    hall, created = lobby()
    room = hall.get_or_create("shared")
    assert room.id == "shared"
    assert created == [room]


def test_get_or_create_returns_the_same_room_the_second_time():
    hall, created = lobby()
    first = hall.get_or_create("shared")
    second = hall.get_or_create("shared")
    assert first is second
    assert created == [first]  # not created twice


def test_a_tick_advances_every_room():
    hall, created = lobby()
    hall.create()
    hall.create()
    hall.tick(33)
    assert all(room.ticks == [33] for room in created)


def test_an_emptied_room_is_forgotten():
    hall, _ = lobby()
    room = hall.create()
    room.is_empty = True
    hall.tick(1)
    assert hall.room(room.id) is None


def test_room_count_reflects_what_is_live():
    hall, _ = lobby()
    assert hall.room_count() == 0
    hall.create()
    hall.create()
    assert hall.room_count() == 2


class FakeActiveRooms:
    def __init__(self):
        self.started = []
        self.ended = []

    def mark_started(self, room_id):
        self.started.append(room_id)

    def mark_ended(self, room_id):
        self.ended.append(room_id)

    def count(self):
        return len(self.started) - len(self.ended)


def test_creating_a_room_marks_it_started_in_the_registry():
    active_rooms = FakeActiveRooms()
    hall = Lobby(lambda room_id: FakeRoom(room_id), "test-server", active_rooms)
    room = hall.create()
    assert active_rooms.started == [room.id]


def test_an_emptied_room_is_marked_ended_in_the_registry():
    active_rooms = FakeActiveRooms()
    hall = Lobby(lambda room_id: FakeRoom(room_id), "test-server", active_rooms)
    room = hall.create()
    room.is_empty = True
    hall.tick(1)
    assert active_rooms.ended == [room.id]


def test_fleet_room_count_reads_the_registry_not_the_local_map():
    active_rooms = FakeActiveRooms()
    hall = Lobby(lambda room_id: FakeRoom(room_id), "test-server", active_rooms)
    hall.create()
    hall.create()
    assert hall.fleet_room_count() == 2


class FakeSnapshots:
    def __init__(self, saved=None):
        self.saved = saved or {}
        self.deleted = []

    def load(self, room_id):
        return self.saved.get(room_id)

    def delete(self, room_id):
        self.deleted.append(room_id)
        self.saved.pop(room_id, None)


def test_a_room_missing_locally_is_rehydrated_from_its_snapshot():
    snapshots = FakeSnapshots({"stale-room": {"pieces": []}})
    rehydrated = []

    def rehydrate(room_id, snapshot):
        room = FakeRoom(room_id)
        rehydrated.append((room_id, snapshot))
        return room

    hall = Lobby(lambda room_id: FakeRoom(room_id), "test-server", snapshots=snapshots, rehydrate=rehydrate)
    room = hall.room("stale-room")
    assert room is not None
    assert rehydrated == [("stale-room", {"pieces": []})]
    assert hall.room("stale-room") is room  # cached, not rehydrated twice


def test_a_room_with_no_saved_snapshot_is_still_missing():
    snapshots = FakeSnapshots()
    hall = Lobby(
        lambda room_id: FakeRoom(room_id), "test-server",
        snapshots=snapshots, rehydrate=lambda room_id, snapshot: FakeRoom(room_id),
    )
    assert hall.room("never-existed") is None


def test_without_snapshots_configured_a_miss_is_just_a_miss():
    hall, _ = lobby()  # no snapshots/rehydrate given
    assert hall.room("anything") is None


def test_an_emptied_room_has_its_snapshot_deleted_not_just_forgotten():
    snapshots = FakeSnapshots()
    hall = Lobby(lambda room_id: FakeRoom(room_id), "test-server", snapshots=snapshots)
    room = hall.create()
    room.is_empty = True
    hall.tick(1)
    assert snapshots.deleted == [room.id]
