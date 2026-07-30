"""Logging in over HTTP before the game socket opens - the client's half of the
API Gateway. `decide` is the pure part, tested without a network; `http_login`
is the real call.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request


def decide(status, payload):
    """(token, new_account) from a login response, or None when refused."""
    if status != 200:
        return None
    return payload["token"], payload["new_account"]


def http_login(config, username, password):  # pragma: no cover - real network I/O
    body = json.dumps({"username": username, "password": password}).encode("utf-8")
    request = urllib.request.Request(
        config.API_LOGIN_URL, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request) as response:
            return decide(response.status, json.loads(response.read()))
    except urllib.error.HTTPError as error:
        return decide(error.code, json.loads(error.read()))
