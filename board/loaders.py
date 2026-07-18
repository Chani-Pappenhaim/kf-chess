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


def csv_to_token(code):
    
    if len(code) != 2:
        raise BoardParseError("UNKNOWN_TOKEN")
    kind, color = code[0], code[1].lower()
    return color + kind


def load_csv_board(rows, registry, config):
    """Adapter that converts CSV board rows into the internal Board. """
    valid_tokens = _valid_text_tokens(registry, config.COLORS, config.EMPTY_CELL)
    grid = []
    width = None
    for line in rows:
        line = line.strip()
        if line == "":
            continue
        tokens = []
        for field in line.split(","):
            field = field.strip()
            tokens.append(config.EMPTY_CELL if field == "" else csv_to_token(field))
        if width is None:
            width = len(tokens)
        elif len(tokens) != width:
            raise BoardParseError("ROW_WIDTH_MISMATCH")
        for token in tokens:
            if token not in valid_tokens:
                raise BoardParseError("UNKNOWN_TOKEN")
        grid.append(tokens)
    return Board(grid, empty_token=config.EMPTY_CELL)


def load_text_board(rows, registry, config):
    """Adapter that converts text board rows into the internal Board."""
    valid_tokens = _valid_text_tokens(registry, config.COLORS, config.EMPTY_CELL)
    grid = []
    width = None
    for line in rows:
        tokens = line.split()
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
    return Board(grid, empty_token=config.EMPTY_CELL)
