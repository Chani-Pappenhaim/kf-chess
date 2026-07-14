import os

import numpy as np
import pytest

from config import settings
from graphics.assets import AssetLoader, read_image, _white_to_alpha


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


def test_white_to_alpha_keys_out_white_and_keeps_body():
    array = np.full((2, 2, 3), 255, dtype=np.uint8)
    array[0, 0] = (10, 10, 10)  # a dark body pixel
    out = _white_to_alpha(array)
    assert out.shape[2] == 4
    assert out[0, 0, 3] == 255  # body stays opaque
    assert out[1, 1, 3] == 0    # white becomes transparent


def test_white_to_alpha_passthrough_when_already_bgra():
    array = np.zeros((2, 2, 4), dtype=np.uint8)
    assert _white_to_alpha(array) is array


def test_asset_loader_loads_every_state_for_a_piece():
    library = AssetLoader(settings).load_sprite_library()
    for state in ("idle", "move", "jump", "short_rest", "long_rest"):
        assert library.has("wP", state)
    anim = library.animation("wP", "idle")
    assert anim.frame_count == 5


def test_asset_loader_skips_non_piece_entries(tmp_path):
    root = tmp_path / "pieces"
    root.mkdir()
    (root / "NOTES.txt").write_text("stray file, not a piece folder")

    class _Config:
        PIECES_ROOT = str(root)
        CELL_SIZE = settings.CELL_SIZE

    library = AssetLoader(_Config()).load_sprite_library()
    assert not library.has("wP", "idle")
