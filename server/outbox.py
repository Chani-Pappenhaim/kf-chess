"""Lines waiting to go out.

The game runs as ordinary blocking code and announces things the moment they
happen; sending them takes an await. Rather than make the game asynchronous,
whoever wants to send drops a line here and the socket loop drains it.

A line is addressed to one client or to everyone, which is the whole difference
between an answer and an announcement.
"""
from __future__ import annotations


class Outbox:
    def __init__(self):
        self._lines = []

    def to_all(self, line):
        """Queue `line` for every connected client."""
        self._lines.append((None, line))

    def to(self, client, line):
        """Queue `line` for one client - the answer to something it asked."""
        self._lines.append((client, line))

    def drain(self):
        """Take everything queued so far, leaving the outbox empty.

        Taken in one go, so a line queued while these are being sent waits for
        the next drain instead of extending this one.
        """
        lines, self._lines = self._lines, []
        return lines
