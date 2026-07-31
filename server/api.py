"""The API Gateway: login, health, and metrics over HTTP - the non-realtime
side of the server. The game socket only ever admits an already-issued token.
"""
from __future__ import annotations

import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
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


def handle_health():
    """The liveness check: this process can answer at all."""
    return 200, {"status": "ok"}


def handle_metrics(service):
    """The autoscaling signal (this server's own rooms), plus the fleet-wide
    count for a dashboard - the same number when there is only one server."""
    return 200, {
        "active_rooms": service.active_rooms(),
        "fleet_active_rooms": service.fleet_active_rooms(),
    }


class ApiGateway:  # pragma: no cover - http shell, exercised by running it
    def __init__(self, config, store, tokens, service):
        self._config = config
        self._store = store
        self._tokens = tokens
        self._service = service

    def start(self):
        """Serve /login, /health, /metrics on a background thread; the game
        socket runs the rest.

        Accepting a connection is cheap, but a login does real CPU work
        (pbkdf2) - so ThreadingHTTPServer's one-thread-per-connection stays for
        the socket itself, while the hashing that thread submits is bounded to
        a pool sized to the actual CPU parallelism available. Past that many
        concurrent logins, the extras wait their turn in the pool's queue
        instead of every request spawning another thread that only adds
        context-switching, not throughput, once every core is already busy.
        """
        hashing = ThreadPoolExecutor(max_workers=os.cpu_count())
        handler = _handler_for(self._store, self._tokens, self._service, self._config, hashing)
        httpd = ThreadingHTTPServer((self._config.API_HOST, self._config.API_PORT), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()


def _handler_for(store, tokens, service, config, hashing):  # pragma: no cover - http shell
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self._reply(*handle_health())
            elif self.path == "/metrics":
                self._reply(*handle_metrics(service))
            else:
                self._reply(404, {"reason": "not found"})

        def do_POST(self):
            if self.path != "/login":
                self._reply(404, {"reason": "not found"})
                return
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            status, payload = hashing.submit(handle_login, store, tokens, config, body).result()
            time.sleep(random.uniform(config.LOGIN_JITTER_MIN_MS, config.LOGIN_JITTER_MAX_MS) / 1000)
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

    return Handler
