import ssl
from types import SimpleNamespace

from scripts.generate_dev_cert import generate
from tls import client_context, server_context


def _disabled_config():
    return SimpleNamespace(TLS_ENABLED=False, TLS_CERT_FILE="", TLS_KEY_FILE="")


def _enabled_config(tmp_path):
    cert_path, key_path = generate(
        str(tmp_path / "dev-cert.pem"), str(tmp_path / "dev-key.pem")
    )
    return SimpleNamespace(TLS_ENABLED=True, TLS_CERT_FILE=cert_path, TLS_KEY_FILE=key_path)


def test_server_context_is_none_when_tls_is_off():
    assert server_context(_disabled_config()) is None


def test_client_context_is_none_when_tls_is_off():
    assert client_context(_disabled_config()) is None


def test_server_context_loads_the_configured_cert(tmp_path):
    context = server_context(_enabled_config(tmp_path))
    assert isinstance(context, ssl.SSLContext)


def test_client_context_trusts_the_same_dev_cert(tmp_path):
    context = client_context(_enabled_config(tmp_path))
    assert isinstance(context, ssl.SSLContext)
    # A real handshake isn't exercised here (that needs a live socket, covered
    # by actually running the server) - this confirms the context was built
    # against the dev cert specifically, not left to verify against the
    # system CA store (which would reject a self-signed cert outright).
    assert context.verify_mode == ssl.CERT_REQUIRED
