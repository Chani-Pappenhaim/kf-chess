"""Generates a self-signed TLS certificate/key pair for local `wss://`
development - not tied to any external CA, so it needs nothing beyond the
`cryptography` package already in requirements.txt (no system `openssl`
binary, so this works identically on Windows dev and the Linux container).

Run once: `python scripts/generate_dev_cert.py`. Writes certs/dev-cert.pem
and certs/dev-key.pem (both gitignored - see .gitignore). A real deployment
uses a CA-issued certificate instead (e.g. cert-manager + Let's Encrypt in
k8s); this is for local `wss://` testing only.
"""
from __future__ import annotations

import datetime
import ipaddress
import os

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CERT_DIR = os.path.join(_PROJECT_ROOT, "certs")
_CERT_PATH = os.path.join(_CERT_DIR, "dev-cert.pem")
_KEY_PATH = os.path.join(_CERT_DIR, "dev-key.pem")
_VALID_DAYS = 365


def generate(cert_path=_CERT_PATH, key_path=_KEY_PATH):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "kfchess-dev"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=_VALID_DAYS))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
    with open(cert_path, "wb") as handle:
        handle.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as handle:
        handle.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    return cert_path, key_path


if __name__ == "__main__":  # pragma: no cover - a one-off local dev script
    cert_path, key_path = generate()
    print(f"wrote {cert_path}\nwrote {key_path}")
