"""The one failure the protocol has.

Anything arriving from outside can be malformed, and every module here refuses
it the same way, so a caller catches one exception for the whole boundary.
"""
from __future__ import annotations


class ProtocolError(ValueError):
    """Raised when text or data cannot be read as the message it claims to be."""
