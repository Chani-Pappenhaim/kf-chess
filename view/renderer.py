class BoardRenderer:
    """Turns a GameSnapshot into printable text.

    Consumes only a snapshot, never a live Board, so the format can change on its
    own.
    """

    def render(self, snapshot):
        return "\n".join(" ".join(row) for row in snapshot.cells)
