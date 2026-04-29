"""Integration tests for config JSON API routes."""

from pathlib import Path
from typing import cast


def test_get_config_returns_json_shape(client, temp_config_path: Path):
    response = client.get("/api/config")

    assert response.status_code == 200
    data = cast(dict, response.get_json())
    assert "content" in data
    assert isinstance(data["content"], str)
    assert len(data["content"]) > 0


def test_put_config_valid_yaml_persists(client, temp_config_path: Path):
    cfg = temp_config_path
    text = cfg.read_text(encoding="utf-8")
    payload = {"content": text + "\n# api test marker\n"}

    put_response = client.put("/api/config", json=payload)
    assert put_response.status_code == 200
    put_data = cast(dict, put_response.get_json())
    assert put_data.get("ok") is True

    get_response = client.get("/api/config")
    assert get_response.status_code == 200
    get_data = cast(dict, get_response.get_json())
    assert "# api test marker" in get_data["content"]


def test_put_config_invalid_yaml_returns_400(client, temp_config_path: Path):
    response = client.put(
        "/api/config",
        json={"content": "this is: not: valid yaml: [[["},
    )

    assert response.status_code == 400
    data = cast(dict, response.get_json())
    assert "error" in data
    assert "message" in data["error"]
