"""Asset loading for the graphical UI.

Loading images lives here rather than in Img (the drawing primitive) so the two
responsibilities stay separate. Images are read with ``np.fromfile`` +
``cv2.imdecode`` instead of ``cv2.imread`` because OpenCV's imread cannot open
paths containing non-ASCII characters on Windows, and this project's own path
may contain them. cv2 stays confined to the graphics layer.
"""
from __future__ import annotations

import cv2
import numpy as np

from graphics.img import Img


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
