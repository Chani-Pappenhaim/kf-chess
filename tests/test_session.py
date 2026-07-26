import pytest

from accounts.store import Account
from config import settings
from protocol.errors import ProtocolError
from protocol.messages import (
    CreateRoom,
    JoinRoom,
    MoveRequest,
    Rejected,
    SeekGame,
    decode,
    encode,
)
from server.session import ClientSession
from view.render_model import RenderModel


class FakeEngine:
    def render_model(self):
        return RenderModel(pieces=(), width=8, height=8)


class FakeRoom:
    def __init__(self, room_id="1"):
        self.id = room_id
        self.joined = []
        self.left = []

    def join(self, session):
        self.joined.append(session)

    def leave(self, session):
        self.left.append(session)


class FakeLobby:
    def __init__(self, existing=None):
        self.created = []
        self._existing = existing or {}

    def create(self):
        room = FakeRoom(str(len(self.created) + 1))
        self.created.append(room)
        return room

    def room(self, room_id):
        return self._existing.get(room_id)


class FakeMatchmaker:
    def __init__(self):
        self.sought = []
        self.cancelled = []

    def seek(self, session):
        self.sought.append(session)

    def cancel(self, session):
        self.cancelled.append(session)


def session(lobby=None, matchmaker=None):
    sent = []
    lobby = lobby or FakeLobby()
    matchmaker = matchmaker or FakeMatchmaker()
    client = ClientSession(Account("dana", 1200), lobby, matchmaker, sent.append, settings)
    return client, lobby, matchmaker, sent


def test_play_asks_the_matchmaker_to_seek():
    client, _lobby, mm, _sent = session()
    client.handle(encode(SeekGame()))
    assert mm.sought == [client]


def test_create_opens_a_room_and_joins_it():
    client, lobby, _mm, _sent = session()
    client.handle(encode(CreateRoom()))
    assert lobby.created[0].joined == [client]


def test_join_enters_the_named_room():
    room = FakeRoom("7")
    client, _lobby, _mm, _sent = session(lobby=FakeLobby({"7": room}))
    client.handle(encode(JoinRoom("7")))
    assert room.joined == [client]


def test_joining_a_missing_room_is_refused():
    client, _lobby, _mm, sent = session(lobby=FakeLobby({}))
    client.handle(encode(JoinRoom("nope")))
    assert decode(sent[-1]) == Rejected(settings.REJECT_NO_SUCH_ROOM)


def test_a_game_command_on_the_home_screen_is_refused():
    client, _lobby, _mm, _sent = session()
    with pytest.raises(ProtocolError):
        client.handle(encode(MoveRequest("WPa2a3")))


def test_a_session_carries_its_account():
    client, _lobby, _mm, _sent = session()
    assert client.account.username == "dana"


def test_entering_a_room_records_the_colour():
    client, _lobby, _mm, _sent = session()
    client.enter_room(FakeRoom(), "b", object(), 8)
    assert client.color == "b"


def test_a_game_command_in_a_room_is_forwarded_to_the_game():
    # Routed to the room's CommandHandler; on an empty board it does nothing,
    # but it flows through and returns rather than being treated as a lobby line.
    client, _lobby, _mm, _sent = session()
    client.enter_room(FakeRoom(), "w", FakeEngine(), 8)
    client.handle(encode(MoveRequest("WPa2a3")))  # no piece there -> a no-op


def test_once_in_a_room_lobby_commands_no_longer_apply():
    # In a room every line is a game command, so a home-screen message is now
    # something the game handler does not understand.
    client, _lobby, _mm, _sent = session()
    client.enter_room(FakeRoom(), "w", object(), 8)
    with pytest.raises(ProtocolError):
        client.handle(encode(SeekGame()))


def test_send_reaches_this_clients_own_wire():
    # A room broadcasts through each member's send; this is that seam.
    client, _lobby, _mm, sent = session()
    client.send("a line")
    assert sent == ["a line"]


def test_departing_from_the_home_screen_leaves_the_queue():
    client, _lobby, mm, _sent = session()
    client.depart()
    assert mm.cancelled == [client]


def test_departing_from_a_room_leaves_the_room():
    room = FakeRoom()
    client, _lobby, _mm, _sent = session()
    client.enter_room(room, "w", object(), 8)
    client.depart()
    assert room.left == [client]
