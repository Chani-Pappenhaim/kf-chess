"""Storing a password without keeping the password.

A password is never stored as itself. It is run through a slow one-way hash with
a random salt, and only the salt and the hash are kept; the original cannot be
read back from them. To check a password later, the same hash is applied to the
attempt and compared.

pbkdf2 (from the standard library) is the slow one-way hash - deliberately
expensive, so guessing at the stored value is expensive too. No dependency is
added for this.
"""
from __future__ import annotations

import hashlib
import hmac
import os

_ALGORITHM = "sha256"
_ITERATIONS = 200_000  # how many rounds pbkdf2 runs; higher is slower to guess
_SALT_BYTES = 16
_SEPARATOR = "$"


def hash_password(password):
    """The stored form of `password`: a fresh salt and the hash under it, so the
    same password hashes differently every time and stored values never collide."""
    salt = os.urandom(_SALT_BYTES)
    digest = _pbkdf2(password, salt)
    return f"{salt.hex()}{_SEPARATOR}{digest.hex()}"


def verify(password, stored):
    """Whether `password` is the one `stored` was made from.

    The salt travels inside `stored`, so the attempt is hashed the same way and
    compared. A malformed stored value simply fails to verify rather than raising,
    so bad data in the store can never crash a login.
    """
    salt_hex, _, digest_hex = stored.partition(_SEPARATOR)
    if not digest_hex:
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    # Constant-time compare, so a wrong guess cannot be narrowed by timing.
    return hmac.compare_digest(_pbkdf2(password, salt), expected)


def _pbkdf2(password, salt):
    return hashlib.pbkdf2_hmac(_ALGORITHM, password.encode("utf-8"), salt, _ITERATIONS)
