import importlib.util

import pytest

# Skip by default to avoid requiring FastAPI during standard test runs.
pytestmark = pytest.mark.skip(reason="web gateway smoke test (enable manually)")

fastapi_spec = importlib.util.find_spec("fastapi")

if fastapi_spec is not None:
    from fastapi.testclient import TestClient
    from server.webapp import app


def test_join_command_and_state_flow():
    if fastapi_spec is None:
        pytest.skip("fastapi not installed")

    client = TestClient(app)

    create_resp = client.post("/lobbies", json={"name": "Smoke Table"})
    assert create_resp.status_code == 200
    lobby_payload = create_resp.json()

    list_resp = client.get("/lobbies")
    assert list_resp.status_code == 200
    assert "lobbies" in list_resp.json()

    join_resp = client.post("/join", json={"name": "WebTester", "lobby_id": lobby_payload["lobby_id"]})
    assert join_resp.status_code == 200
    payload = join_resp.json()
    token = payload["token"]
    assert payload["player_id"] in (1, 2, 3, 4)
    assert payload["lobby_id"] == lobby_payload["lobby_id"]

    cmd_resp = client.post("/command", json={"token": token, "command": "list players"})
    assert cmd_resp.status_code == 200
    assert "Player" in cmd_resp.json()["message"] or cmd_resp.json()["message"] == ""

    updates_resp = client.get("/updates", params={"token": token})
    assert updates_resp.status_code == 200

    state_resp = client.get("/state", params={"token": token})
    assert state_resp.status_code == 200
    state_data = state_resp.json()
    assert "lobby_id" in state_data
    assert "lobby_name" in state_data
    assert "player_id" in state_data
    assert "scoreboard" in state_data
    assert "round_score" in state_data
    assert "host_id" in state_data
    assert "max_players" in state_data
    assert "can_start" in state_data
    assert "players" in state_data
    assert "phase" in state_data
    assert "hand" in state_data
    assert "playable_cards" in state_data
    assert "table_slots" in state_data
    assert "last_winner" in state_data
    assert "last_trick_winning_card" in state_data
    assert "highlight_until" in state_data
    assert "recent_trick" in state_data
    assert "recent_trick_expire" in state_data
    if state_data["players"]:
        player_entry = state_data["players"][0]
        assert "ping" in player_entry
        assert "ok" in player_entry


def test_leave_room_updates_seats_and_deletes_empty_lobby():
    if fastapi_spec is None:
        pytest.skip("fastapi not installed")

    client = TestClient(app)

    create_resp = client.post("/lobbies", json={"name": "Leave Table"})
    lobby_id = create_resp.json()["lobby_id"]

    join_one = client.post("/join", json={"name": "Alpha", "lobby_id": lobby_id}).json()
    join_two = client.post("/join", json={"name": "Beta", "lobby_id": lobby_id}).json()

    leave_resp = client.post("/leave", json={"token": join_one["token"]})
    assert leave_resp.status_code == 200

    state_resp = client.get("/state", params={"token": join_two["token"]})
    assert state_resp.status_code == 200
    state_data = state_resp.json()
    assert state_data["player_id"] == 1
    assert [player["name"] for player in state_data["players"]] == ["Beta"]

    final_leave = client.post("/leave", json={"token": join_two["token"]})
    assert final_leave.status_code == 200

    list_resp = client.get("/lobbies")
    lobbies_payload = list_resp.json()["lobbies"]
    assert all(lobby["lobby_id"] != lobby_id for lobby in lobbies_payload)
