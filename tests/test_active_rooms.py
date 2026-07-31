from server.active_rooms import InMemoryActiveRooms


def test_a_started_room_counts():
    rooms = InMemoryActiveRooms()
    rooms.mark_started("a")
    assert rooms.count() == 1


def test_an_ended_room_stops_counting():
    rooms = InMemoryActiveRooms()
    rooms.mark_started("a")
    rooms.mark_ended("a")
    assert rooms.count() == 0


def test_marking_the_same_room_started_twice_counts_once():
    rooms = InMemoryActiveRooms()
    rooms.mark_started("a")
    rooms.mark_started("a")
    assert rooms.count() == 1


def test_ending_a_room_never_marked_started_is_a_no_op():
    rooms = InMemoryActiveRooms()
    rooms.mark_ended("never-was")
    assert rooms.count() == 0
