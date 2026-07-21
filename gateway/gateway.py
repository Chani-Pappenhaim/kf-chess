"""GameGateway - the seam between the UI and the game logic.

A contract only (no logic): the UI depends on this Protocol, never on the
concrete GameEngine, so the single copy of the game logic can be reached
in-process today and over a network later. GameEngine already exposes exactly
these methods, so it satisfies the contract with no wrapper class. A future
NetworkGateway will implement the same methods over the wire, forwarding to an
engine running on a server - see NetworkGateway below.

It is deliberately message/DTO based: commands take plain cells, replies are a
MoveResult or the immutable RenderModel, and no live Board or arbiter object
ever crosses the seam - which is what keeps the networked implementation clean.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from game.models import MoveResult
from view.render_model import RenderModel


@runtime_checkable
class GameGateway(Protocol):
    def request_move(self, start, end) -> MoveResult:
        ...

    def request_jump(self, cell) -> MoveResult:
        ...

    def wait(self, dt) -> None:
        ...

    def render_model(self) -> RenderModel:
        ...


class NetworkGateway:
    """Planned remote implementation of GameGateway (not yet built).

    Documented here to make the extension point explicit: it will implement the
    same five methods, serialising each command and returning the MoveResult /
    RenderModel received from a server that runs the authoritative GameEngine.
    Because the engine is deterministic and its clock is injected via wait(dt),
    the server can order contested moves by timestamp and every client converges
    to the same state. No UI code changes when this replaces the local engine.
    """

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "NetworkGateway is a planned extension; use a GameEngine "
            "(the in-process GameGateway) for now."
        )
