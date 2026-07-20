"""SpriteLibrary - looks up a loaded animation by piece token and state.

The translation boundary on the sprite side: the code speaks internal tokens
("wP", "bK"), while the asset folders are named the other way round ("PW",
"KB"). token_to_code bridges the two, so no caller knows the on-disk naming.
Holds already-loaded animations only; loading them is AssetLoader's job.
"""
from __future__ import annotations


def token_to_code(token):
    """Internal token -> asset folder code ("wP" -> "PW")."""
    color, kind = token[0], token[1]
    return kind + color.upper()


class SpriteLibrary:
    def __init__(self, animations):
        # animations: dict keyed by (asset_code, state) -> SpriteAnimation
        self._animations = dict(animations)

    def animation(self, token, state):
        return self._animations[(token_to_code(token), state)]

    def has(self, token, state):
        return (token_to_code(token), state) in self._animations
