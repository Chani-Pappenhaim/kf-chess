"""KungFu Chess - a networked client. Run with `python -m client`.

The fourth entry point, and the only one with no game inside it: no board, no
rules, no clock. It sends what the player does and draws what it is told.

Login is asked in the shell (username, then a masked password) and sent over
HTTP to the API Gateway, which answers with a token - the game socket never
sees the password. Then a home screen offers two ways into a game - Play for a
quick match, or Room to create or join one by id - and once in a room the same
window play.py uses draws the game, unaware it is remote. Everything above the
gateway is the same code the local game runs.
"""
from __future__ import annotations

from client.gateway import NetworkGateway
from client.home import HomeScreen, run_home
from client.identity import Identity
from client.inbox import Inbox
from client.login import http_login
from client.password import read_password
from client.router import MessageRouter
from client.socket import WebSocketClient
from client.waiting import wait_for_state, waiting_canvas
from config import settings
from events.bus import EventBus
from graphics.room_dialog import ask_room
from graphics.window import Window
from interaction.board_mapper import BoardMapper
from interaction.controller import Controller
from logs.activity_log import file_log, silent_log
from protocol.messages import Connect, CreateRoom, JoinRoom, SeekGame, encode
from ui.composition import board_origin, build_loop


def build_client(config=settings, log=None):
    """The client's half of the graph, minus the window.

    The bus is the client's own. Events arriving from the server are published
    onto it, so sound and banners subscribe exactly as they do locally. The log
    records every line the socket sends or receives; without one wired it is
    silent, so the code paths are the same either way.
    """
    log = log or silent_log()
    inbox, bus, identity = Inbox(), EventBus(), Identity()
    router = MessageRouter(inbox, bus, identity)
    socket = WebSocketClient(config, router, log, identity.connection_lost)
    gateway = NetworkGateway(inbox, socket.send)
    return inbox, bus, identity, socket, gateway


def run(config=settings, ask=input, ask_secret=read_password, login=http_login):  # pragma: no cover - real-time GUI loop
    username = ask(config.USERNAME_PROMPT).strip() or "guest"
    password = ask_secret(config.PASSWORD_PROMPT)
    result = login(config, username, password)
    if result is None:
        print(config.REJECT_WRONG_PASSWORD)
        return
    token, new_account = result
    print(_greeting(config, new_account).format(name=username))

    window = Window(config.WINDOW_TITLE)
    try:
        join_room_id = None
        while True:
            log = file_log(config.CLIENT_LOG_PATH, "kfchess.client")
            inbox, bus, identity, socket, gateway = build_client(config, log)
            socket.start()
            socket.send(encode(Connect(token)))  # the opening line the server expects
            if not _await_login(window, identity, config):
                _report_failure(identity)
                return
            entered = (
                _join_directly(window, socket.send, identity, config, join_room_id)
                if join_room_id is not None
                else _pick_and_enter(window, socket.send, identity, config)
            )
            if not entered:
                _report_failure(identity)
                return
            join_room_id = identity.redirect_room_id()
            if join_room_id is None:  # entered a room here - no redirect pending
                break
        _play(window, gateway, inbox, bus, identity, config)
        _report_failure(identity)
    finally:
        window.close()


# -- shell / screen flow (all real-time GUI, so untested) -------------------

def _await_login(window, identity, config):  # pragma: no cover
    """Hold the connecting screen until the server accepts the login."""
    while True:
        if identity.logged_in():
            return True
        if identity.rejected() or identity.lost():
            return False
        window.show(waiting_canvas(config, config.CONNECTING_TEXT))
        for event in window.poll_events():
            if event[0] == "quit":
                return False


def _pick_and_enter(window, send, identity, config):  # pragma: no cover
    """The home screen: choose Play or Room until one puts us in a room. Returns
    True once in a room, False if the window is closed or the connection drops."""
    home = HomeScreen(config)
    while True:
        identity.retry()
        choice = run_home(window, home)
        if choice is None:
            return False
        if choice == "play":
            identity.seeking()
            send(encode(SeekGame()))
        elif not _ask_room(send, config):
            continue  # dialog cancelled - back to the home screen
        if _await_room(window, identity, config):
            return True
        if identity.lost():
            return False


def _ask_room(send, config):  # pragma: no cover
    """Open the Room dialog and send the chosen command. False if cancelled."""
    action, room_id = ask_room(config)
    if action is None:
        return False
    send(encode(CreateRoom() if action == "create" else JoinRoom(room_id)))
    return True


def _await_room(window, identity, config):  # pragma: no cover
    """Wait after Play/Create/Join until the server seats us, redirects us to
    a match on another server, or the attempt fails (no opponent, no such
    room, a drop, or the window closing)."""
    while True:
        if identity.in_room() or identity.redirect_room_id() is not None:
            return True
        if identity.no_opponent() or identity.rejected() or identity.lost():
            return False
        window.show(waiting_canvas(config, config.SEARCHING_TEXT))
        for event in window.poll_events():
            if event[0] == "quit":
                return False


def _join_directly(window, send, identity, config, room_id):  # pragma: no cover
    """Reconnect after a Redirected: skip the home screen and join straight."""
    send(encode(JoinRoom(room_id)))
    return _await_room(window, identity, config)


def _play(window, gateway, inbox, bus, identity, config):  # pragma: no cover
    """Draw the game until it ends, the window closes, or the connection drops."""
    model = wait_for_state(window, inbox, identity, config)
    if model is None:
        return
    controller = Controller(
        gateway,
        BoardMapper(model, config.CELL_SIZE, board_origin(config)),
        own_color=identity.color(),
        spectator=identity.is_spectator(),
    )
    build_loop(
        window, gateway, controller, bus, config,
        own_color=identity.color(), room_id=identity.room_id(),
        spectator=identity.is_spectator(),
        alive=lambda: not identity.lost(),
    ).run()


def _greeting(config, new_account):  # pragma: no cover
    return config.ACCOUNT_CREATED_MESSAGE if new_account else config.WELCOME_BACK_MESSAGE


def _report_failure(identity):  # pragma: no cover
    """Print why we stopped, if it was a refusal or a dropped connection."""
    reason = identity.rejection_reason() or identity.loss_reason()
    if reason is not None:
        print(reason)


if __name__ == "__main__":  # pragma: no cover
    run()
