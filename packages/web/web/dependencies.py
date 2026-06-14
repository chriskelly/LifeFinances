from __future__ import annotations

from pathlib import Path

from core.repository import PlanRepository


def get_repository(db_path: Path) -> PlanRepository:
    return PlanRepository(db_path=db_path)
