"""Builds the `ssl.SSLContext` every socket shell needs, from `config`, in one
place - `server/socket.py`, `server/ws_gateway.py`, `server/api.py`, and
`client/socket.py` all read the same two settings
(`TLS_CERT_FILE`/`TLS_KEY_FILE`), so this is where "how they turn into a
context" lives instead of being copied into each. A top-level module (not
under `server/` or `client/`) because both sides need it and neither is
supposed to import from the other.
"""
from __future__ import annotations

import ssl


def server_context(config):
    """The context a listening socket wraps itself in, or None when TLS is
    off - every caller already checks `config.TLS_ENABLED` first, so this
    only ever runs when both files are actually configured."""
    if not config.TLS_ENABLED:
        return None
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(config.TLS_CERT_FILE, config.TLS_KEY_FILE)
    return context


def client_context(config):
    """The context an outgoing connection verifies the server against - the
    dev cert itself, not the system CA store, since `scripts/generate_dev_cert.py`
    is self-signed. A real deployment's client would use
    `ssl.create_default_context()` unmodified (a CA-issued cert verifies
    against the system trust store like any other HTTPS site); this trusts
    the dev cert specifically instead, which is what makes it a *real*
    handshake rather than `_create_unverified_context()` disabling
    verification altogether."""
    if not config.TLS_ENABLED:
        return None
    return ssl.create_default_context(cafile=config.TLS_CERT_FILE)
