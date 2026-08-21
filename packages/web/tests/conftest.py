from pathlib import Path

import pytest
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from fastapi.testclient import TestClient
from web.app import create_app


@pytest.fixture
def client(db_path: Path) -> TestClient:
    app = create_app(db_path=db_path)
    return TestClient(app)


@pytest.fixture
def plan_id(db_path: Path) -> int:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    new_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    return new_id
