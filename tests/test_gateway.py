import pytest

import play
from config import settings
from gateway.gateway import GameGateway, NetworkGateway


def test_game_engine_satisfies_the_gateway_contract():
    engine = play.build_engine(settings)
    assert isinstance(engine, GameGateway)  # structural match, no wrapper needed


def test_network_gateway_is_a_documented_stub():
    with pytest.raises(NotImplementedError):
        NetworkGateway()
