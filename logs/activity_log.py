"""A record of everything that crosses the wire, kept on each side.

Both the server and the client write one of these, so the whole conversation
between them survives on disk for inspection afterwards. The log itself is pure -
it is handed a `write` callable and only decides what each line says, so it is
tested without a file; `file_log` is the thin shell that points it at a real one,
exactly as read_password wires masked() to a real console.
"""
from __future__ import annotations


class ActivityLog:
    def __init__(self, write):
        self._write = write

    def sent(self, line):
        """A line this side put on the wire."""
        self._write("sent " + line)

    def received(self, line):
        """A line this side took off the wire."""
        self._write("recv " + line)

    def note(self, text):
        """Something worth recording that is not a wire line - a connection
        opening or closing."""
        self._write(text)


def file_log(path, name):  # pragma: no cover - real file I/O
    """An ActivityLog that appends timestamped lines to `path`. `name` keeps the
    two sides' loggers apart so their handlers never cross."""
    import logging

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
    return ActivityLog(logger.info)


def silent_log():
    """An ActivityLog that records nothing - the default when no file is wired,
    so the code paths stay identical whether or not logging is on."""
    return ActivityLog(lambda line: None)
