from board.board import Board


class BoardParseError(Exception):
    """Raised when external board input is malformed for its format."""


def _valid_text_tokens(registry, colors, empty_token):
    """All the tokens that are valid in text/CSV board input.
    Each token is a two-character string: the piece kind followed by the color."""
    tokens = {empty_token}
    for color in colors:
        for kind in registry.registered_kinds():
            tokens.add(color + kind)
    return tokens


def _build_board(rows, parse_line, valid_tokens, empty_token):
    """Shared loading skeleton: everything a loader does apart from its format.

    A loader supplies only `parse_line`, which turns one input line into a list
    of internal tokens (an empty list for a line that carries no cells). The
    contract every format shares - skip blank lines, board must be rectangular,
    every token must be recognised - lives here once, so adding a format is
    writing a `parse_line` and nothing else, and a fix to the contract cannot
    be applied to one loader while the other is forgotten.
    """
    grid = []
    width = None
    for line in rows:
        tokens = parse_line(line)
        if not tokens:
            continue
        if width is None:
            width = len(tokens)
        elif len(tokens) != width:
            raise BoardParseError("ROW_WIDTH_MISMATCH")
        for token in tokens:
            if token not in valid_tokens:
                raise BoardParseError("UNKNOWN_TOKEN")
        grid.append(tokens)
    return Board(grid, empty_token=empty_token)


def csv_to_token(code):
    # The external asset form is KIND+COLOUR ("QW"); the internal token is
    # colour+kind ("wQ"). graphics.sprite_library.token_to_code is the inverse of
    # this, for the sprite folders, which share the same naming - change one and
    # check the other. They are not unified: board must not depend on graphics,
    # and it is two lines either way.
    if len(code) != 2:
        raise BoardParseError("UNKNOWN_TOKEN")
    kind, color = code[0], code[1].lower()
    return color + kind


def load_csv_board(rows, registry, config):
    """Adapter that converts CSV board rows into the internal Board.

    Comma-separated cells, an empty field meaning an empty square, and piece
    codes in the external KIND+COLOR form (translated by csv_to_token).
    """
    def parse_line(line):
        line = line.strip()
        if line == "":
            return []
        return [
            config.EMPTY_CELL if field == "" else csv_to_token(field)
            for field in (f.strip() for f in line.split(","))
        ]

    return _build_board(
        rows,
        parse_line,
        _valid_text_tokens(registry, config.COLORS, config.EMPTY_CELL),
        config.EMPTY_CELL,
    )


def load_text_board(rows, registry, config):
    """Adapter that converts text board rows into the internal Board.

    Whitespace-separated cells already written in the internal color+kind form,
    with the empty-cell token spelled out.
    """
    return _build_board(
        rows,
        lambda line: line.split(),
        _valid_text_tokens(registry, config.COLORS, config.EMPTY_CELL),
        config.EMPTY_CELL,
    )
