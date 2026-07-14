from board.board import Board


class BoardParseError(Exception):
    """Raised when external board input is malformed for its format."""


def _valid_text_tokens(registry, colors, empty_token):
    """Valid tokens are derived from whatever piece kinds are registered,
    rather than a hardcoded string - so registering a custom piece kind
    automatically makes its token accepted here too.
    """
    tokens = {empty_token}
    for color in colors:
        for kind in registry.registered_kinds():
            tokens.add(color + kind)
    return tokens


def _ctd26_code_to_token(code):
    """Translate a CTD26 board.csv cell code into an internal Board token.

    CTD26 encodes a piece as KIND+COLOR in upper case (e.g. "PW", "KB"),
    while the internal Board uses color+kind (e.g. "wP", "bK") because the
    whole engine treats ``token[0]`` as the color. The two formats are a 1:1
    mapping, translated here at the adapter boundary so no game-logic module
    ever sees the external format.
    """
    if len(code) != 2:
        raise BoardParseError("UNKNOWN_TOKEN")
    kind, color = code[0], code[1].lower()
    return color + kind


def load_csv_board(rows, registry, config):
    """Adapter that converts CTD26 CSV board rows into the internal Board.

    Sibling of load_text_board for the ``board.csv`` format shipped with the
    CTD26 assets: comma-separated cells, an empty field meaning an empty
    square, and piece codes in CTD26's KIND+COLOR form (translated to internal
    tokens via _ctd26_code_to_token). Same validation contract as the text
    loader: rectangular board, every token recognised by the registry.
    """
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
            tokens.append(config.EMPTY_CELL if field == "" else _ctd26_code_to_token(field))
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
    """Adapter that converts text board rows into the internal Board.

    This is the text-format seam. To support another input format (e.g. a
    binary board) add a sibling loader that likewise returns a Board; no
    game-logic module needs to change, only main.py picks which loader to use.

    Validates that the board is rectangular and that every token is one the
    registry recognises, raising BoardParseError otherwise.
    """
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
