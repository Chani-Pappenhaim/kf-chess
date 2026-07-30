from accounts.store import Account
from config import settings
from protocol.messages import NoOpponent, Redirected, decode
from server.allocator import GameAllocator
from server.matchmaking import Matchmaker
from server.matchmaking_queue import InMemoryMatchmakingQueue
from server.pubsub import InMemoryPubSub


class FakeRoom:
    def __init__(self, room_id):
        self.id = room_id
        self.joined = []

    def join(self, session):
        self.joined.append(session)


class FakeLobby:
    def __init__(self):
        self.rooms = []

    def get_or_create(self, room_id):
        for room in self.rooms:
            if room.id == room_id:
                return room
        room = FakeRoom(room_id)
        self.rooms.append(room)
        return room


class FakeSession:
    def __init__(self, username, rating):
        self.account = Account(username, rating)
        self.sent = []

    def send(self, line):
        self.sent.append(line)


def maker():
    lobby = FakeLobby()
    queue = InMemoryMatchmakingQueue(settings)
    allocator = GameAllocator(["only"])  # one server: every room hashes to it
    return Matchmaker(lobby, queue, settings, allocator, "only"), lobby


def test_two_seekers_in_range_share_one_new_room():
    mm, lobby = maker()
    first, second = FakeSession("dana", 1200), FakeSession("yossi", 1250)
    mm.seek(first)
    mm.seek(second)
    assert len(lobby.rooms) == 1
    assert lobby.rooms[0].joined == [first, second]


def test_a_seeker_out_of_rating_range_keeps_waiting():
    mm, lobby = maker()
    mm.seek(FakeSession("dana", 1200))
    mm.seek(FakeSession("yossi", 1400))  # 200 apart, beyond the range
    assert lobby.rooms == []


def test_a_seeker_is_told_no_one_was_found_after_the_timeout():
    mm, _ = maker()
    seeker = FakeSession("dana", 1200)
    mm.seek(seeker)
    mm.tick(settings.MATCHMAKING_TIMEOUT_MS)
    assert isinstance(decode(seeker.sent[-1]), NoOpponent)


def test_a_seeker_is_not_timed_out_early():
    mm, _ = maker()
    seeker = FakeSession("dana", 1200)
    mm.seek(seeker)
    mm.tick(settings.MATCHMAKING_TIMEOUT_MS - 1)
    assert seeker.sent == []


def test_a_match_from_another_server_is_handed_back_without_a_bus():
    # A shared queue can hold a seeker whose session lives on another Game
    # Server; with no bus to reach them, both sides just wait normally.
    lobby = FakeLobby()
    queue = InMemoryMatchmakingQueue(settings)
    queue.add("ghost", 1200)
    mm = Matchmaker(lobby, queue, settings, GameAllocator(["only"]), "only")

    mm.seek(FakeSession("dana", 1200))

    assert lobby.rooms == []
    assert queue.pop_match(1200) == ("ghost", 1200)  # handed back
    assert queue.pop_match(1200) == ("dana", 1200)   # this seeker also waits


def test_a_cross_server_match_seats_one_side_and_redirects_the_other():
    # Two Matchmakers sharing a queue and a ring - exactly two Game Servers.
    # Each gets its own bus subscription over a shared broker, exactly as two
    # separate processes each open their own RedisPubSub to the same channel.
    queue = InMemoryMatchmakingQueue(settings)
    broker = {}
    allocator = GameAllocator(["a", "b"])
    lobby_a, lobby_b = FakeLobby(), FakeLobby()
    mm_a = Matchmaker(lobby_a, queue, settings, allocator, "a", InMemoryPubSub(broker))
    mm_b = Matchmaker(lobby_b, queue, settings, allocator, "b", InMemoryPubSub(broker))

    ghost, dana = FakeSession("ghost", 1200), FakeSession("dana", 1200)
    mm_b.seek(ghost)  # waits, session lives on "server B"
    mm_a.seek(dana)   # "server A" finds ghost's entry and places the room
    mm_a.tick(1)       # drain the bus on both sides, whichever needed it
    mm_b.tick(1)

    rooms = lobby_a.rooms + lobby_b.rooms
    assert len(rooms) == 1
    room_id = rooms[0].id
    seated = {s.account.username for s in rooms[0].joined}
    redirected = {
        s.account.username for s in (ghost, dana)
        if s.sent and decode(s.sent[-1]) == Redirected(room_id)
    }
    assert len(seated) == 1 and len(redirected) == 1
    assert seated | redirected == {"ghost", "dana"}


def test_a_local_match_placed_on_a_third_server_gets_both_redirected_and_hosted():
    # Both seekers are on the same server, but the hash sends their room
    # elsewhere - that server must still open it, or neither can ever join.
    queue = InMemoryMatchmakingQueue(settings)
    broker = {}
    ring = GameAllocator(["c"])  # every room hashes to "c" no matter what
    lobby_a, lobby_c = FakeLobby(), FakeLobby()
    mm_a = Matchmaker(lobby_a, queue, settings, ring, "a", InMemoryPubSub(broker))
    mm_c = Matchmaker(lobby_c, queue, settings, ring, "c", InMemoryPubSub(broker))

    dana, yossi = FakeSession("dana", 1200), FakeSession("yossi", 1200)
    mm_a.seek(dana)
    mm_a.seek(yossi)  # matched locally on "a", but the room belongs on "c"

    assert lobby_a.rooms == []  # not hosted where the match was found
    room_id = decode(dana.sent[-1]).room_id
    assert decode(yossi.sent[-1]) == Redirected(room_id)

    mm_c.tick(1)  # "c" drains the bus and opens the room before anyone arrives
    assert lobby_c.rooms and lobby_c.rooms[0].id == room_id
    assert lobby_c.rooms[0].joined == []  # reserved, not yet joined by either


def test_a_cancelled_seeker_leaves_the_queue():
    mm, lobby = maker()
    gone = FakeSession("dana", 1200)
    mm.seek(gone)
    mm.cancel(gone)
    mm.seek(FakeSession("yossi", 1200))
    assert lobby.rooms == []  # nobody left to match the newcomer with
