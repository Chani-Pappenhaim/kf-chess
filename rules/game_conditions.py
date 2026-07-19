from abc import ABC, abstractmethod


class WinCondition(ABC):
    """Decides whether a capture ends the game."""

    @abstractmethod
    def is_game_over(self, captured_piece):
        """`captured_piece` is the token just captured, or None."""


class KingCaptureWinCondition(WinCondition):
    def is_game_over(self, captured_piece):
        return captured_piece is not None and captured_piece[1] == "K"


class PromotionRule(ABC):
    """Decides whether a piece transforms on arrival, and into what."""

    @abstractmethod
    def promote(self, piece, row, board_height):
        """Return the piece token after promotion, unchanged if none applies."""


class LastRankPromotion(PromotionRule):
    """Promotes a pawn that reaches the far edge in its direction of travel.

    The promotion rank comes from the same per-color direction that drives
    movement, so flipping that direction moves promotion along with it.
    """

    def __init__(self, directions, promotable_kind="P", promote_to="Q"):
        self._directions = directions
        self._promotable_kind = promotable_kind
        self._promote_to = promote_to

    def promote(self, piece, row, board_height):
        color, kind = piece[0], piece[1]
        if kind != self._promotable_kind:
            return piece
        last_rank = 0 if self._directions[color] < 0 else board_height - 1
        if row == last_rank:
            return color + self._promote_to
        return piece
    