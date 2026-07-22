"""Reading a password in the shell, showing an asterisk per key.

getpass shows nothing at all, which reads as "it took nothing"; this echoes a
star for each character so there is visible proof the input landed, while the
password itself never appears on screen.

The loop is pure - it is handed a read-a-key function and a write function, so
it is tested without a real terminal. read_password wires it to the Windows
console; on anything without msvcrt it falls back to getpass.
"""
from __future__ import annotations

_ENTER = ("\r", "\n")
_BACKSPACE = ("\b", "\x7f")
_INTERRUPT = "\x03"


def masked(prompt, read_key, write):
    """Read a line, echoing '*' per key. `read_key` returns one character at a
    time; `write` prints without a newline of its own."""
    write(prompt)
    chars = []
    while True:
        key = read_key()
        if key in _ENTER:
            write("\n")
            return "".join(chars)
        if key == _INTERRUPT:
            raise KeyboardInterrupt
        if key in _BACKSPACE:
            if chars:
                chars.pop()
                write("\b \b")  # step back, erase the star, step back again
        else:
            chars.append(key)
            write("*")


def read_password(prompt):  # pragma: no cover - real console I/O
    """Ask for a password at a real terminal, masked with asterisks. Best run
    from a Windows console (PowerShell or cmd); without msvcrt it falls back to
    getpass, which hides the input entirely."""
    import sys

    try:
        import msvcrt
    except ImportError:
        from getpass import getpass
        return getpass(prompt)

    def write(text):
        sys.stdout.write(text)
        sys.stdout.flush()

    return masked(prompt, msvcrt.getwch, write)
