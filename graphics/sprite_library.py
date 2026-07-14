"""SpriteLibrary - lookup of loaded animations by piece token and state.

This is the sprite-side translation boundary: the rest of the code speaks the
internal board token ("wP", "bK"), while the asset folders are named in CTD26's
KIND+COLOR form ("PW", "KB"). token_to_code bridges the two so no caller needs
to know the on-disk naming. Holds already-loaded animations only - loading them
from disk is AssetLoader's job (graphics/assets.py).
"""
from __future__ import annotations


def token_to_code(token):
    """Internal board token -> CTD26 asset folder code ("wP" -> "PW")."""
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
