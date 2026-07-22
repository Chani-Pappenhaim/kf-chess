"""KungFu Chess - a networked client. Run with `python -m client`.

The fourth entry point, and the only one with no game inside it: no board, no
rules, no clock. It sends what the player does and draws what it is told.

Login is asked in the shell, not the window, as the slide asks: a username is
read, sent as the first line, and the server answers with a colour or a refusal.
Everything above the gateway is the same code play.py runs - the window cannot
tell which of the two it is drawing.
"""
from __future__ import annotations

from getpass import getpass

from client.gateway import NetworkGateway
from client.identity import Identity
from client.inbox import Inbox
from client.router import MessageRouter
from client.socket import WebSocketClient
from client.waiting import wait_for_state
from config import settings
from events.bus import EventBus
from interaction.board_mapper import BoardMapper
from interaction.controller import Controller
from graphics.window import Window
from protocol.messages import Login, encode
from ui.composition import board_origin, build_loop


def build_client(config=settings):
    """The client's half of the graph, minus the window.

    The bus is the client's own. Events arriving from the server are published
    onto it, so sound and banners subscribe exactly as they do locally.
    """
    inbox, bus, identity = Inbox(), EventBus(), Identity()
    socket = WebSocketClient(config, MessageRouter(inbox, bus, identity))
    gateway = NetworkGateway(inbox, socket.send)
    return inbox, bus, identity, socket, gateway


def run(config=settings, ask=input, ask_secret=getpass):  # pragma: no cover - real-time GUI loop
    # Login is asked in the shell, not the window; the password is read without
    # echo. A new username registers, a known one must match.
    username = ask("username: ").strip() or "guest"
    password = ask_secret("password: ")
    inbox, bus, identity, socket, gateway = build_client(config)

    socket.start()
    socket.send(encode(Login(username, password)))  # the opening line the server expects

    window = Window(config.WINDOW_TITLE)
    try:
        model = wait_for_state(window, inbox, identity, config)
        if model is None:
            if identity.rejected():
                print(identity.rejection_reason())
            return

        # The model gives the board's extent, which is all the mapper needs; the
        # client has no board of its own. The colour gates which pieces this
        # player may pick up.
        controller = Controller(
            gateway,
            BoardMapper(model, config.CELL_SIZE, board_origin(config)),
            own_color=identity.color(),
        )
        build_loop(window, gateway, controller, bus, config).run()
    finally:
        window.close()


if __name__ == "__main__":  # pragma: no cover
    run()
