"""GameGateway - the seam between the UI and the game logic.

A contract only (no logic): the UI depends on this Protocol, never on the
concrete GameEngine, so the single copy of the game logic can be reached
in-process (GameEngine) or over a network (client.gateway.NetworkGateway)
with no UI code change.

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

    def render_model(self) -> RenderModel:
        ...
