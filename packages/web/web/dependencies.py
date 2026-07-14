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
    plan_repo.ensure_bootstrap(settings_repo=settings_repo)
    settings = settings_repo.get()
    summaries = plan_repo.list()
    ids = {summary.id for summary in summaries}
    default_id = settings.default_plan_id
    if default_id in ids:
        return default_id
    fallback = min(ids)
    settings_repo.save(settings.model_copy(update={"default_plan_id": fallback}))
    return fallback


def require_plan(plan_id: int, *, plan_repo: PlanRepository) -> tuple[int, Plan]:
    plan = plan_repo.get_by_id(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan_id, plan
