from config import settings
from server.api import handle_health, handle_history, handle_login, handle_metrics, handle_metrics_prometheus
from server.tokens import InMemoryTokenStore
from tests.support import FakeAccountStore, FakeHistoryStore


def login(store, tokens, username, password):
    return handle_login(store, tokens, settings, {"username": username, "password": password})


def test_a_new_username_is_registered_and_given_a_token():
    status, payload = login(FakeAccountStore(settings.STARTING_RATING), InMemoryTokenStore(), "dana", "pw")
    assert status == 200
    assert payload["new_account"] is True
    assert payload["token"]


def test_a_returning_user_with_the_right_password_gets_a_token():
    store = FakeAccountStore(settings.STARTING_RATING)
    store.register("dana", "pw")
    status, payload = login(store, InMemoryTokenStore(), "dana", "pw")
    assert status == 200
    assert payload["new_account"] is False


def test_a_wrong_password_is_refused_with_no_token():
    store = FakeAccountStore(settings.STARTING_RATING)
    store.register("dana", "secret")
    status, payload = login(store, InMemoryTokenStore(), "dana", "wrong")
    assert status == 401
    assert payload == {"reason": settings.REJECT_WRONG_PASSWORD}


def test_the_issued_token_resolves_to_the_account():
    tokens = InMemoryTokenStore()
    _status, payload = login(FakeAccountStore(settings.STARTING_RATING), tokens, "dana", "pw")
    assert tokens.resolve(payload["token"]).username == "dana"


def test_health_reports_ok():
    assert handle_health() == (200, {"status": "ok"})


class _FakeService:
    def active_rooms(self):
        return 7

    def fleet_active_rooms(self):
        return 19


def test_metrics_reports_the_active_room_count():
    assert handle_metrics(_FakeService()) == (200, {"active_rooms": 7, "fleet_active_rooms": 19})


def test_prometheus_metrics_exposes_active_rooms_in_exposition_format():
    status, body = handle_metrics_prometheus(_FakeService())
    assert status == 200
    assert "active_rooms 7" in body
    assert "# TYPE active_rooms gauge" in body


def test_history_requires_a_username():
    status, payload = handle_history(FakeHistoryStore(), None, settings)
    assert status == 400


def test_history_reports_a_players_recent_games():
    history = FakeHistoryStore()
    history.record("dana", "yossi", None, 1000)
    status, payload = handle_history(history, "dana", settings)
    assert status == 200
    assert payload["games"] == [{"winner": "dana", "loser": "yossi", "reason": None, "ended_at": 1000}]


def test_history_is_empty_for_a_player_with_no_games():
    status, payload = handle_history(FakeHistoryStore(), "nobody", settings)
    assert status == 200
    assert payload["games"] == []
