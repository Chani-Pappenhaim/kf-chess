"""KungFu Chess - a networked client. Run with `python -m client`.

The fourth entry point, and the only one with no game inside it: no board, no
rules, no clock. It sends what the player does and draws what it is told.

Everything above the gateway is the same code play.py runs. That is the whole
point of the seam: the window cannot tell which of the two it is drawing.
"""
from __future__ import annotations

from client.gateway import NetworkGateway
from client.inbox import Inbox
from client.router import MessageRouter
from client.socket import WebSocketClient
from client.waiting import wait_for_state
from config import settings
from events.bus import EventBus
from game.board_mapper import BoardMapper
from game.controller import Controller
from graphics.window import Window
from ui.composition import board_origin, build_loop


def build_client(config=settings):
    """The client's half of the graph, minus the window.

    The bus is the client's own. Events arriving from the server are published
    onto it, so sound and banners subscribe exactly as they do locally.
    """
    inbox, bus = Inbox(), EventBus()
    socket = WebSocketClient(config, MessageRouter(inbox, bus))
    gateway = NetworkGateway(inbox, socket.send)
    return inbox, bus, socket, gateway


def run(config=settings):  # pragma: no cover - real-time GUI loop
    inbox, bus, socket, gateway = build_client(config)
    socket.start()

    window = Window(config.WINDOW_TITLE)
    try:
        model = wait_for_state(window, inbox, config)
        if model is None:
            return  # closed before the game ever arrived

        # The model is what the mapper measures clicks against: the client has
        # no board of its own, and needs none - only the board's extent.
        controller = Controller(
            gateway, BoardMapper(model, config.CELL_SIZE, board_origin(config))
        )
        build_loop(window, gateway, controller, bus, config).run()
    finally:
        window.close()


if __name__ == "__main__":  # pragma: no cover
    run()
