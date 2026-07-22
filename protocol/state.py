"""The render model as plain data, and back.

This is the game state a server sends and a client draws. Only built-in types
cross - dicts, lists, numbers, strings - so the message survives JSON and
neither side needs the other's classes to read it.

Cells travel as two-element lists, because JSON has no tuples, and come back as
tuples, because that is what the rest of the code compares and looks up with.
"""
from __future__ import annotations

from game.move_log import MoveRecord
from view.render_model import RenderModel, RenderPiece


def encode_model(model):
    """A RenderModel as plain data."""
    return {
        "pieces": [_encode_piece(piece) for piece in model.pieces],
        "width": model.width,
        "height": model.height,
        "game_over": model.game_over,
        "clock": model.clock,
        "moves": [_encode_move(record) for record in model.moves],
        "scores": dict(model.scores),
        "players": dict(model.players),
        "ratings": dict(model.ratings),
    }


def decode_model(data):
    """Plain data back into a RenderModel."""
    return RenderModel(
        pieces=tuple(_decode_piece(piece) for piece in data["pieces"]),
        width=data["width"],
        height=data["height"],
        game_over=data["game_over"],
        clock=data["clock"],
        moves=tuple(_decode_move(record) for record in data["moves"]),
        scores=dict(data["scores"]),
        players=dict(data["players"]),
        ratings=dict(data["ratings"]),
    )


def _encode_piece(piece):
    return {
        "token": piece.token,
        "cell": _cell_to_wire(piece.cell),
        "state": piece.state,
        "target": _cell_to_wire(piece.target),
        "progress": piece.progress,
        "cooldown_progress": piece.cooldown_progress,
    }


def _decode_piece(data):
    return RenderPiece(
        token=data["token"],
        cell=_cell_from_wire(data["cell"]),
        state=data["state"],
        target=_cell_from_wire(data["target"]),
        progress=data["progress"],
        cooldown_progress=data["cooldown_progress"],
    )


def _encode_move(record):
    return {
        "color": record.color,
        "notation": record.notation,
        "time_ms": record.time_ms,
    }


def _decode_move(data):
    return MoveRecord(
        color=data["color"],
        notation=data["notation"],
        time_ms=data["time_ms"],
    )


def _cell_to_wire(cell):
    # `target` is absent on a piece that is not stepping anywhere.
    return None if cell is None else list(cell)


def _cell_from_wire(cell):
    return None if cell is None else tuple(cell)
