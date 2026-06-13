from __future__ import annotations

from pathlib import Path

import pytest
from core.db_bootstrap import materialize_blank_db
from core.repository import PlanRepository


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return materialize_blank_db(tmp_path / "data.db")


@pytest.fixture
def repo(db_path: Path) -> PlanRepository:
    return PlanRepository(db_path=db_path)
