from __future__ import annotations

from pathlib import Path

from core.models import Plan
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from fastapi import HTTPException


def get_repository(db_path: Path) -> PlanRepository:
    return PlanRepository(db_path=db_path)


def resolve_default_plan_id(
    *, plan_repo: PlanRepository, settings_repo: SettingsRepository
) -> int:
    default_plan_id, _ = plan_repo.ensure_bootstrap(settings_repo=settings_repo)
    return default_plan_id


def require_plan(plan_id: int | None, *, plan_repo: PlanRepository) -> tuple[int, Plan]:
    if plan_id is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan = plan_repo.get_by_id(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan_id, plan
