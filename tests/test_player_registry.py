from server.registry import PlayerRegistry

COLORS = ("w", "b")


def test_the_first_to_join_takes_the_first_colour():
    registry = PlayerRegistry(COLORS)
    assert registry.join("dana") == "w"


def test_the_second_takes_the_next():
    registry = PlayerRegistry(COLORS)
    registry.join("dana")
    assert registry.join("yossi") == "b"


def test_a_third_is_turned_away():
    registry = PlayerRegistry(COLORS)
    registry.join("dana")
    registry.join("yossi")
    assert registry.join("latecomer") is None


def test_names_map_each_colour_to_who_holds_it():
    registry = PlayerRegistry(COLORS)
    registry.join("dana")
    registry.join("yossi")
    assert registry.names() == {"w": "dana", "b": "yossi"}


def test_leaving_reopens_the_seat():
    registry = PlayerRegistry(COLORS)
    registry.join("dana")     # white
    registry.join("yossi")    # black
    registry.leave("w")
    assert registry.join("chani") == "w"
    assert registry.names() == {"b": "yossi", "w": "chani"}


def test_leaving_a_free_seat_changes_nothing():
    registry = PlayerRegistry(COLORS)
    registry.join("dana")
    registry.leave("b")  # nobody is black
    assert registry.names() == {"w": "dana"}
