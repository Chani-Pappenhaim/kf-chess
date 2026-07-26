from client.gateway import NetworkGateway
from client.identity import Identity
from client.inbox import Inbox
from client.router import MessageRouter
from client.__main__ import build_client
from config import settings
from events.bus import EventBus
from gateway.gateway import GameGateway
from game.events import GameStarted
from protocol.events import encode_event
from protocol.messages import EventNotice, RoomEntered, encode


def test_the_client_graph_is_wired_without_connecting():
    # Nothing here opens a socket: building the client and connecting it are
    # separate, which is what makes the whole graph testable.
    inbox, bus, identity, socket, gateway = build_client(settings)
    assert isinstance(inbox, Inbox)
    assert isinstance(bus, EventBus)
    assert isinstance(identity, Identity)
    assert isinstance(gateway, GameGateway)


def test_a_command_from_the_gateway_is_queued_by_the_socket():
    inbox, _bus, _id, socket, gateway = build_client(settings)
    from view.render_model import RenderModel, RenderPiece

    inbox.receive_state(RenderModel(
        pieces=(RenderPiece("wP", (6, 4)),), width=8, height=8
    ))
    gateway.request_jump((6, 4))
    assert socket._outgoing.qsize() == 1


def test_an_event_off_the_wire_reaches_the_client_bus():
    # End to end on the client side: a line the server would have sent lands
    # on this client's own bus, where sound and banners are subscribed.
    inbox, bus, identity, socket, _gateway = build_client(settings)
    seen = []
    bus.subscribe(GameStarted, seen.append)

    MessageRouter(inbox, bus, identity).route(
        encode(EventNotice(encode_event(GameStarted(at_ms=7))))
    )

    assert seen == [GameStarted(at_ms=7)]


def test_the_room_colour_is_what_the_client_will_play():
    inbox, bus, identity, socket, _gateway = build_client(settings)
    MessageRouter(inbox, bus, identity).route(encode(RoomEntered("b", "7", False)))
    assert identity.color() == "b"
