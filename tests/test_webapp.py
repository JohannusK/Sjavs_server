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

    join_resp = client.post("/join", json={"name": "WebTester"})
    assert join_resp.status_code == 200
    payload = join_resp.json()
    token = payload["token"]
    assert payload["player_id"] in (1, 2, 3, 4)

    cmd_resp = client.post("/command", json={"token": token, "command": "list players"})
    assert cmd_resp.status_code == 200
    assert "Player" in cmd_resp.json()["message"] or cmd_resp.json()["message"] == ""

    updates_resp = client.get("/updates", params={"token": token})
    assert updates_resp.status_code == 200

    state_resp = client.get("/state", params={"token": token})
    assert state_resp.status_code == 200
    state_data = state_resp.json()
    assert "scoreboard" in state_data
    assert "players" in state_data
    assert "phase" in state_data
    assert "hand" in state_data
    assert "table_slots" in state_data
    assert "last_winner" in state_data
    assert "highlight_until" in state_data
    if state_data["players"]:
        player_entry = state_data["players"][0]
        assert "ping" in player_entry
        assert "ok" in player_entry
