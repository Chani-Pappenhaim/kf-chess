from dataclasses import dataclass


@dataclass(frozen=True)
class MoveResult:
    """The engine's answer to a command: accepted, or why it was refused.

    The refusal may come from the rules or from the engine's own guards; either
    way it is a code from rules.reasons.
    """

    is_accepted: bool
    reason: str
