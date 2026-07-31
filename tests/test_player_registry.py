from accounts.store import Account
from server.registry import PlayerRegistry

COLORS = ("w", "b")


def account(username, rating=1200):
    return Account(username, rating)


def test_the_first_to_join_takes_the_first_colour():
    registry = PlayerRegistry(COLORS)
    assert registry.seat(account("dana")) == "w"


def test_the_second_takes_the_next():
    registry = PlayerRegistry(COLORS)
    registry.seat(account("dana"))
    assert registry.seat(account("yossi")) == "b"


def test_a_third_is_turned_away():
    registry = PlayerRegistry(COLORS)
    registry.seat(account("dana"))
    registry.seat(account("yossi"))
    assert registry.seat(account("latecomer")) is None


def test_names_map_each_colour_to_who_holds_it():
    registry = PlayerRegistry(COLORS)
    registry.seat(account("dana"))
    registry.seat(account("yossi"))
    assert registry.names() == {"w": "dana", "b": "yossi"}


def test_ratings_map_each_colour_to_its_rating():
    registry = PlayerRegistry(COLORS)
    registry.seat(account("dana", 1300))
    registry.seat(account("yossi", 1100))
    assert registry.ratings() == {"w": 1300, "b": 1100}


def test_name_of_reads_one_seat():
    registry = PlayerRegistry(COLORS)
    registry.seat(account("dana"))
    assert registry.name_of("w") == "dana"
    assert registry.name_of("b") is None


def test_a_new_rating_replaces_the_cached_one():
    registry = PlayerRegistry(COLORS)
    registry.seat(account("dana", 1200))
    registry.set_rating("w", 1216)
    assert registry.ratings() == {"w": 1216}


def test_setting_the_rating_of_an_empty_seat_does_nothing():
    registry = PlayerRegistry(COLORS)
    registry.set_rating("w", 1500)  # nobody is white
    assert registry.ratings() == {}


def test_leaving_reopens_the_seat():
    registry = PlayerRegistry(COLORS)
    registry.seat(account("dana"))     # white
    registry.seat(account("yossi"))    # black
    registry.leave("w")
    assert registry.seat(account("chani")) == "w"
    assert registry.names() == {"b": "yossi", "w": "chani"}


def test_one_player_cannot_take_both_colours():
    # The same person on two connections must not play against themselves: once
    # seated, a second seat is refused even though a colour is free.
    registry = PlayerRegistry(COLORS)
    assert registry.seat(account("dana")) == "w"
    assert registry.seat(account("dana")) is None
    assert registry.names() == {"w": "dana"}


def test_the_freed_seat_can_be_retaken_by_the_same_name():
    # Refusing a duplicate must not lock a name out for good: after leaving, that
    # player can sit again (e.g. reconnecting).
    registry = PlayerRegistry(COLORS)
    registry.seat(account("dana"))
    registry.leave("w")
    assert registry.seat(account("dana")) == "w"


def test_seated_color_finds_a_still_seated_player():
    registry = PlayerRegistry(COLORS)
    registry.seat(account("dana"))
    assert registry.seated_color("dana") == "w"


def test_seated_color_is_none_for_an_empty_seat():
    registry = PlayerRegistry(COLORS)
    assert registry.seated_color("dana") is None
