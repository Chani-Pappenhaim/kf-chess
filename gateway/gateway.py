"""GameGateway - the seam between the UI and the game logic.

A contract only (no logic): the UI depends on this Protocol, never on the
concrete GameEngine, so the single copy of the game logic can be reached
in-process today and over a network later. GameEngine already exposes exactly
these methods, so it satisfies the contract with no wrapper class. A future
NetworkGateway will implement the same methods over the wire, forwarding to an
engine running on a server - see NetworkGateway below.

Commands are sent, not asked: they report nothing back, because a remote one
could not answer in time to be useful. Everything the UI learns, it learns from
the render model. GameEngine still returns a MoveResult to its own callers; the
UI is simply not one of them.

It is deliberately message/DTO based: commands take plain cells, the reply is
the immutable RenderModel, and no live Board or arbiter object ever crosses the
seam - which is what keeps the networked implementation clean.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from view.render_model import RenderModel


@runtime_checkable
class GameGateway(Protocol):
    def legal_targets(self, cell) -> tuple:
        ...

    def request_move(self, start, end) -> None:
        ...

    def request_jump(self, cell) -> None:
        ...

    def wait(self, dt) -> None:
        ...

    def render_model(self) -> RenderModel:
        ...


class NetworkGateway:
    """Planned remote implementation of GameGateway (not yet built).

    Documented here to make the extension point explicit: a remote proxy that
    serialises each command to a server running the authoritative GameEngine,
    and answers every query from the last state that server sent back. Because
    the engine's clock is injected via wait(dt), the server alone advances time
    and every client draws the state it is given. No UI code changes when this
    replaces the local engine.
    """

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "NetworkGateway is a planned extension; use a GameEngine "
            "(the in-process GameGateway) for now."
        )
