class UnknownPieceKindError(Exception):
    pass


class PieceRuleRegistry:
    """Maps a piece-kind letter to its MovementStrategy.

    The extension point for new piece kinds: registering a kind with its own
    strategy is all it takes. Nothing else branches on the letter, and the board
    loaders derive their valid tokens from what is registered here, so the new
    piece is accepted in board input too.
    """

    def __init__(self):
        self._strategies = {}

    def register(self, kind, strategy):
        self._strategies[kind] = strategy

    def get(self, kind):
        try:
            return self._strategies[kind]
        except KeyError:
            raise UnknownPieceKindError(kind) from None

    def registered_kinds(self):
        return tuple(self._strategies.keys())


def build_default_registry(config):
    """Factory for the standard chess piece set.

    Kept separate from PieceRuleRegistry so a different piece set is assembled
    the same way, without subclassing anything.
    """
    from rules.piece_rules import (
        KingMovement,
        QueenMovement,
        RookMovement,
        BishopMovement,
        KnightMovement,
        PawnMovement,
    )

    registry = PieceRuleRegistry()
    registry.register("K", KingMovement())
    registry.register("Q", QueenMovement())
    registry.register("R", RookMovement())
    registry.register("B", BishopMovement())
    registry.register("N", KnightMovement())
    registry.register("P", PawnMovement(config.PAWN_DIRECTION))
    return registry
