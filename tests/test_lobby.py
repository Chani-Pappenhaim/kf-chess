from server.lobby import Lobby
from server.room_directory import InMemoryRoomDirectory


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

    directory = InMemoryRoomDirectory()
    return Lobby(factory, directory, server_id), created, directory


def test_create_opens_a_room_with_a_fresh_id():
    hall, _, _ = lobby()
    assert hall.create().id != hall.create().id


def test_a_created_room_is_found_by_its_id():
    hall, _, _ = lobby()
    room = hall.create()
    assert hall.room(room.id) is room


def test_an_unknown_id_finds_no_room():
    hall, _, _ = lobby()
    assert hall.room("nope") is None


def test_a_tick_advances_every_room():
    hall, created, _ = lobby()
    hall.create()
    hall.create()
    hall.tick(33)
    assert all(room.ticks == [33] for room in created)


def test_an_emptied_room_is_forgotten():
    hall, _, _ = lobby()
    room = hall.create()
    room.is_empty = True
    hall.tick(1)
    assert hall.room(room.id) is None


def test_a_created_room_is_registered_under_this_server():
    hall, _, directory = lobby(server_id="server-a")
    room = hall.create()
    assert directory.get(room.id) == "server-a"


def test_an_emptied_room_is_removed_from_the_directory():
    hall, _, directory = lobby()
    room = hall.create()
    room.is_empty = True
    hall.tick(1)
    assert directory.get(room.id) is None
