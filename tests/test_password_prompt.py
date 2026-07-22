import pytest

from client.password import masked


def keys(text):
    """A read_key that yields the characters of `text`, one per call."""
    it = iter(text)
    return lambda: next(it)


def recorder():
    out = []
    return out, out.append


def test_it_returns_what_was_typed_up_to_enter():
    assert masked("pw: ", keys("secret\r"), lambda s: None) == "secret"


def test_every_key_echoes_one_star_not_the_character():
    out, write = recorder()
    masked("pw: ", keys("abc\r"), write)
    shown = "".join(out)
    assert "abc" not in shown
    assert shown.count("*") == 3


def test_the_prompt_is_written_first():
    out, write = recorder()
    masked("password: ", keys("x\r"), write)
    assert out[0] == "password: "


def test_backspace_removes_the_last_character():
    # type "ab", backspace, then "c" -> "ac"
    assert masked("", keys("ab\bc\r"), lambda s: None) == "ac"


def test_backspace_on_an_empty_line_does_nothing():
    assert masked("", keys("\b\bhi\r"), lambda s: None) == "hi"


def test_a_newline_also_ends_the_line():
    assert masked("", keys("word\n"), lambda s: None) == "word"


def test_ctrl_c_interrupts():
    with pytest.raises(KeyboardInterrupt):
        masked("", keys("ab\x03"), lambda s: None)
