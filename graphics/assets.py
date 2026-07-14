"""Asset loading for the graphical UI.

Loading images lives here rather than in Img (the drawing primitive) so the two
responsibilities stay separate. Images are read with ``np.fromfile`` +
``cv2.imdecode`` instead of ``cv2.imread`` because OpenCV's imread cannot open
paths containing non-ASCII characters on Windows, and this project's own path
may contain them. cv2 stays confined to the graphics layer.
"""
from __future__ import annotations

import json
import os

import cv2
import numpy as np

from graphics.img import Img
from graphics.sprite import SpriteAnimation
from graphics.sprite_library import SpriteLibrary


def read_image(path, size=None, keep_aspect=False, interpolation=cv2.INTER_AREA):
    """Load an image (Unicode-path safe) into a fresh Img, optionally resized.

    Mirrors Img.read's resize contract: exact resize to ``size`` by default, or
    shrink-to-fit preserving aspect ratio when ``keep_aspect`` is True.
    """
    data = np.fromfile(str(path), dtype=np.uint8)
    array = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if array is None:
        raise FileNotFoundError(f"Not a readable image: {path}")

    if size is not None:
        target_w, target_h = size
        height, width = array.shape[:2]
        if keep_aspect:
            scale = min(target_w / width, target_h / height)
            new_size = (int(width * scale), int(height * scale))
        else:
            new_size = (target_w, target_h)
        array = cv2.resize(array, new_size, interpolation=interpolation)

    img = Img()
    img.img = array
    return img


def _white_to_alpha(array, threshold=250):
    """Add an alpha channel to a 3-channel sprite, making near-white pixels
    transparent. The placeholder sprites ship on an opaque white background with
    a lighter-grey fill (~230), so keying pure white out lets pieces composite
    onto the board without white boxes while leaving the piece body intact.
    """
    if array.shape[2] == 4:
        return array
    blue, green, red = cv2.split(array)
    near_white = (blue >= threshold) & (green >= threshold) & (red >= threshold)
    alpha = np.where(near_white, 0, 255).astype(np.uint8)
    return cv2.merge([blue, green, red, alpha])


def _frame_paths(sprites_dir):
    """PNG frame files sorted by their numeric name (1.png, 2.png, ...)."""
    names = [n for n in os.listdir(sprites_dir) if n.lower().endswith(".png")]
    names.sort(key=lambda n: int(os.path.splitext(n)[0]))
    return [os.path.join(sprites_dir, n) for n in names]


class AssetLoader:
    """Loads the on-disk piece assets into an in-memory SpriteLibrary.

    Walks assets/pieces/<CODE>/states/<STATE>/, reads each state's config.json
    (fps, loop, next state) and its numbered sprite frames, sizing every frame
    to a board cell and keying out the white background so pieces are drawable
    with alpha. I/O lives here; SpriteLibrary only serves what was loaded.
    """

    def __init__(self, config):
        self._config = config

    def load_sprite_library(self):
        animations = {}
        pieces_root = self._config.PIECES_ROOT
        for code in sorted(os.listdir(pieces_root)):
            states_dir = os.path.join(pieces_root, code, "states")
            if not os.path.isdir(states_dir):
                continue
            for state in sorted(os.listdir(states_dir)):
                animations[(code, state)] = self._load_animation(states_dir, state)
        return SpriteLibrary(animations)

    def _load_animation(self, states_dir, state):
        state_dir = os.path.join(states_dir, state)
        with open(os.path.join(state_dir, "config.json"), encoding="utf-8") as handle:
            config = json.load(handle)
        cell = self._config.CELL_SIZE
        frames = []
        for path in _frame_paths(os.path.join(state_dir, "sprites")):
            frame = read_image(path, size=(cell, cell), keep_aspect=True)
            frame.img = _white_to_alpha(frame.img)
            frames.append(frame)
        graphics = config["graphics"]
        return SpriteAnimation(
            frames=frames,
            fps=graphics["frames_per_sec"],
            loop=graphics["is_loop"],
            next_state=config["physics"]["next_state_when_finished"],
        )
