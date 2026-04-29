"""Integration tests for simulation JSON API."""

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from app.data import constants


@pytest.fixture
def low_trials_config_path(temp_config_path: Path) -> Path:
    """Return temp config path after forcing trial quantity to a low value."""
    raw = yaml.safe_load(constants.SAMPLE_FULL_CONFIG_PATH.read_text(encoding="utf-8"))
    data = cast(dict[str, Any], raw)
    data["trial_quantity"] = 2
    temp_config_path.write_text(yaml.dump(data), encoding="utf-8")
    return temp_config_path


def test_post_simulation_run_returns_shape(client, low_trials_config_path: Path):
    response = client.post("/api/simulation/run")

    assert response.status_code == 200
    body = cast(dict, response.get_json())
    assert "success_percentage" in body
    assert isinstance(body["success_percentage"], str)
    first = body["first_result"]
    assert "columns" in first and "data" in first
    assert isinstance(first["columns"], list)
    assert isinstance(first["data"], list)
    assert len(first["columns"]) > 0
    assert len(first["data"]) > 0


def test_simulation_uses_config_after_put(client, low_trials_config_path: Path):
    """POST must reflect on-disk config written by a prior PUT."""
    cfg = low_trials_config_path
    text = cfg.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not data or not isinstance(data, dict) or "age" not in data:
        pytest.fail("sample config missing age field")
    different_age = data["age"] + 1
    data["age"] = different_age
    new_text = yaml.dump(data)

    put = client.put("/api/config", json={"content": new_text})
    assert put.status_code == 200

    post = client.post("/api/simulation/run")
    assert post.status_code == 200

    disk = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert cast(dict, disk)["age"] == different_age
