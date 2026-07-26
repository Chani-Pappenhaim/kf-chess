from accounts.store import Account
from config import settings
from protocol.messages import NoOpponent, decode
from server.matchmaking import Matchmaker


class FakeRoom:
    def __init__(self):
        self.joined = []

    def join(self, session):
        self.joined.append(session)


class FakeLobby:
    def __init__(self):
        self.rooms = []

    def create(self):
        room = FakeRoom()
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
    return Matchmaker(lobby, settings), lobby


def test_two_seekers_in_range_share_one_new_room():
    mm, lobby = maker()
    first, second = FakeSession("dana", 1200), FakeSession("yossi", 1250)
    mm.seek(first)
    mm.seek(second)
    assert len(lobby.rooms) == 1
    assert lobby.rooms[0].joined == [first, second]  # first waited -> White


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


def test_a_cancelled_seeker_leaves_the_queue():
    mm, lobby = maker()
    gone = FakeSession("dana", 1200)
    mm.seek(gone)
    mm.cancel(gone)
    mm.seek(FakeSession("yossi", 1200))
    assert lobby.rooms == []  # nobody left to match the newcomer with
