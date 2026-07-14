import os

import pytest

from config import settings
from graphics.assets import read_image


def test_read_image_resizes_to_exact_size():
    img = read_image(settings.BOARD_IMAGE, size=(200, 120))
    height, width = img.img.shape[:2]
    assert (width, height) == (200, 120)


def test_read_image_keep_aspect_fits_longer_side():
    # A square target on a non-square source shrinks so the longer side fits
    # while preserving aspect ratio (no exact-fit distortion).
    sprite = os.path.join(
        settings.PIECES_ROOT, "PW", "states", "idle", "sprites", "1.png"
    )
    img = read_image(sprite, size=(64, 64), keep_aspect=True)
    height, width = img.img.shape[:2]
    assert max(width, height) == 64
    assert width <= 64 and height <= 64


def test_read_image_rejects_non_image():
    # imdecode returns None for bytes that are not a decodable image.
    with pytest.raises(FileNotFoundError):
        read_image(settings.BOARD_CSV)
