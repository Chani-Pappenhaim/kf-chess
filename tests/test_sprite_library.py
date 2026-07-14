from graphics.sprite import SpriteAnimation
from graphics.sprite_library import SpriteLibrary, token_to_code


def test_token_to_code_translates_to_asset_folder_name():
    assert token_to_code("wP") == "PW"
    assert token_to_code("bK") == "KB"


def test_lookup_by_internal_token_and_state():
    anim = SpriteAnimation(["frame"], 6, True, "idle")
    library = SpriteLibrary({("PW", "idle"): anim})
    assert library.animation("wP", "idle") is anim
    assert library.has("wP", "idle")
    assert not library.has("bP", "idle")
