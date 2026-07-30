from server.ws_gateway import parse_pool


def test_a_single_server_parses_to_one_entry():
    assert parse_pool("local=ws://localhost:8765") == {"local": "ws://localhost:8765"}


def test_several_servers_parse_to_several_entries():
    assert parse_pool("a=ws://host-a:8765,b=ws://host-b:8765") == {
        "a": "ws://host-a:8765",
        "b": "ws://host-b:8765",
    }
