from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from web.app import create_app


@pytest.fixture
def client(db_path) -> TestClient:
    app = create_app(db_path=db_path)
    return TestClient(app)
