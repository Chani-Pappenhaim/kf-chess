"""The API Gateway: login over HTTP, so the game socket only ever admits an
already-issued token - nothing else needs the socket.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from server.auth import account_for


def handle_login(store, tokens, config, body):
    """The decision behind POST /login: (status, payload). No I/O of its own,
    so it is tested without opening a port."""
    new_account = not store.exists(body["username"])
    account = account_for(store, body["username"], body["password"])
    if account is None:
        return 401, {"reason": config.REJECT_WRONG_PASSWORD}
    return 200, {"token": tokens.issue(account), "new_account": new_account}


class ApiGateway:  # pragma: no cover - http shell, exercised by running it
    def __init__(self, config, store, tokens):
        self._config = config
        self._store = store
        self._tokens = tokens

    def start(self):
        """Serve /login on a background thread; the game socket runs the rest."""
        handler = _login_handler(self._store, self._tokens, self._config)
        httpd = ThreadingHTTPServer((self._config.API_HOST, self._config.API_PORT), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()


def _login_handler(store, tokens, config):  # pragma: no cover - http shell
    class LoginHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            status, payload = handle_login(store, tokens, config, body)
            self._reply(status, payload)

        def _reply(self, status, payload):
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass  # server.log already covers activity

    return LoginHandler
