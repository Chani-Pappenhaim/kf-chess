import pytest

from graphics.sprite import SpriteAnimation


def _anim(n=5, fps=10, loop=True, next_state="idle"):
    frames = [f"f{i}" for i in range(n)]
    return SpriteAnimation(frames, fps, loop, next_state)


def test_requires_at_least_one_frame():
    with pytest.raises(ValueError):
        SpriteAnimation([], 10, True, "idle")


def test_frame_at_advances_and_clamps_when_not_looping():
    anim = _anim(5, 10, loop=False)  # 10 fps -> 100 ms per frame
    assert anim.frame_at(0) == "f0"
    assert anim.frame_at(150) == "f1"
    assert anim.frame_at(10_000) == "f4"  # clamped to the last frame


def test_frame_at_wraps_when_looping():
    anim = _anim(3, 10, loop=True)  # 3 frames, 100 ms each
    assert anim.frame_at(150) == "f1"
    assert anim.frame_at(300) == "f0"  # wrapped around


def test_duration_and_is_finished():
    anim = _anim(5, 10, loop=False)  # 500 ms total
    assert anim.duration_ms() == 500
    assert not anim.is_finished(499)
    assert anim.is_finished(500)


def test_looping_animation_never_finishes():
    assert not _anim(5, 10, loop=True).is_finished(10_000)


def test_zero_fps_holds_first_frame():
    anim = _anim(5, 0, loop=False)
    assert anim.frame_at(999) == "f0"
    assert anim.duration_ms() == 0


def test_exposes_next_state_and_frame_count():
    anim = _anim(4, next_state="long_rest")
    assert anim.next_state == "long_rest"
    assert anim.frame_count == 4
    assert anim.loop is True
