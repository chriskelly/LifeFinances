from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from core.models import AppSettings, Plan
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from fastapi import Depends, HTTPException, Query, Request


def get_db_path(request: Request) -> Path:
    return request.app.state.db_path


DbPathDep = Annotated[Path, Depends(get_db_path)]


def get_repo(db_path: DbPathDep) -> PlanRepository:
    return PlanRepository(db_path=db_path)


def get_settings_repo(db_path: DbPathDep) -> SettingsRepository:
    return SettingsRepository(db_path=db_path)


RepoDep = Annotated[PlanRepository, Depends(get_repo)]
SettingsRepoDep = Annotated[SettingsRepository, Depends(get_settings_repo)]


def get_settings(settings_repo: SettingsRepoDep) -> AppSettings:
    return settings_repo.get()


SettingsDep = Annotated[AppSettings, Depends(get_settings)]


@dataclass(frozen=True)
class SelectedPlan:
    id: int
    plan: Plan


def _load_or_404(*, repo: PlanRepository, plan_id: int | None) -> SelectedPlan:
    if plan_id is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan = repo.get_by_id(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return SelectedPlan(id=plan_id, plan=plan)


def require_query_plan(
    repo: RepoDep,
    plan: Annotated[int | None, Query()] = None,
) -> SelectedPlan:
    return _load_or_404(repo=repo, plan_id=plan)


def require_path_plan(repo: RepoDep, plan_id: int) -> SelectedPlan:
    return _load_or_404(repo=repo, plan_id=plan_id)


PlanDep = Annotated[SelectedPlan, Depends(require_query_plan)]
PathPlanDep = Annotated[SelectedPlan, Depends(require_path_plan)]
