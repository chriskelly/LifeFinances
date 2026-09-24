from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Annotated

from core.models import Plan
from core.paths import default_db_path
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from simulation.result import SimulationResult

from web.explain import (
    DB_NOT_INITIALIZED,
    DB_NOT_INITIALIZED_MESSAGE,
    HTTP_BAD_REQUEST,
    HTTP_SERVICE_UNAVAILABLE,
    INVALID_QUERY,
    ExplainFailure,
    diagnostics_payload,
    list_loadable_plans,
    load_cached_result,
    resolve_plan,
    series_payload,
    summary_payload,
    validate_series,
)
from web.routes import (
    API_PLAN,
    API_PLANS,
    API_RESULT_DIAGNOSTICS,
    API_RESULT_SERIES,
    API_RESULT_SUMMARY,
)


class _DatabaseNotInitialized(Exception):
    pass


def _require_db_path(request: Request) -> Path:
    db_path = request.app.state.db_path or default_db_path()
    if not db_path.exists():
        raise _DatabaseNotInitialized
    return db_path


DbPathDep = Annotated[Path, Depends(_require_db_path)]


def _get_repo(db_path: DbPathDep) -> PlanRepository:
    return PlanRepository(db_path=db_path)


def _get_settings_repo(db_path: DbPathDep) -> SettingsRepository:
    return SettingsRepository(db_path=db_path)


RepoDep = Annotated[PlanRepository, Depends(_get_repo)]
SettingsRepoDep = Annotated[SettingsRepository, Depends(_get_settings_repo)]


def _json(result: dict[str, object] | ExplainFailure) -> JSONResponse:
    if isinstance(result, ExplainFailure):
        return JSONResponse(status_code=result.status_code, content=result.body())
    return JSONResponse(status_code=200, content=result)


def _scoped(
    *,
    request: Request,
    repo: PlanRepository,
    settings_repo: SettingsRepository,
    plan_id: int | None,
    name: str | None,
) -> ExplainFailure | tuple[int, Plan, SimulationResult]:
    resolved = resolve_plan(plan_repo=repo, plan_id=plan_id, name=name)
    if isinstance(resolved, ExplainFailure):
        return resolved
    resolved_id, plan = resolved
    loaded = load_cached_result(
        app=request.app,
        plan_id=resolved_id,
        plan=plan,
        settings=settings_repo.get(),
    )
    if isinstance(loaded, ExplainFailure):
        return loaded
    return resolved_id, plan, loaded


def register_explain_routes(web_app: FastAPI) -> None:
    @web_app.exception_handler(_DatabaseNotInitialized)
    def database_not_initialized(
        request: Request, exc: _DatabaseNotInitialized
    ) -> JSONResponse:
        del request, exc
        return _json(
            ExplainFailure(
                status_code=HTTP_SERVICE_UNAVAILABLE,
                code=DB_NOT_INITIALIZED,
                message=DB_NOT_INITIALIZED_MESSAGE,
            )
        )

    _register_plan_routes(web_app)
    _register_result_routes(web_app)


def _register_plan_routes(web_app: FastAPI) -> None:
    @web_app.get(API_PLANS)
    def plans(*, repo: RepoDep, settings_repo: SettingsRepoDep) -> JSONResponse:
        listed = list_loadable_plans(plan_repo=repo, settings_repo=settings_repo)
        return _json({"plans": [asdict(item) for item in listed]})

    @web_app.get(API_PLAN)
    def plan(
        *,
        repo: RepoDep,
        plan_id: Annotated[int | None, Query()] = None,
        name: Annotated[str | None, Query()] = None,
    ) -> JSONResponse:
        resolved = resolve_plan(plan_repo=repo, plan_id=plan_id, name=name)
        if isinstance(resolved, ExplainFailure):
            return _json(resolved)
        resolved_id, resolved_plan = resolved
        return _json(
            {
                "plan_id": resolved_id,
                "name": resolved_plan.name,
                "plan": resolved_plan.model_dump(mode="json"),
            }
        )


def _register_result_routes(web_app: FastAPI) -> None:
    @web_app.get(API_RESULT_SUMMARY)
    def summary(
        *,
        request: Request,
        repo: RepoDep,
        settings_repo: SettingsRepoDep,
        plan_id: Annotated[int | None, Query()] = None,
        name: Annotated[str | None, Query()] = None,
    ) -> JSONResponse:
        scoped = _scoped(
            request=request,
            repo=repo,
            settings_repo=settings_repo,
            plan_id=plan_id,
            name=name,
        )
        if isinstance(scoped, ExplainFailure):
            return _json(scoped)
        resolved_id, resolved_plan, result = scoped
        return _json(
            summary_payload(
                plan_id=resolved_id,
                plan_name=resolved_plan.name,
                result=result,
            )
        )

    @web_app.get(API_RESULT_DIAGNOSTICS)
    def diagnostics(
        *,
        request: Request,
        repo: RepoDep,
        settings_repo: SettingsRepoDep,
        plan_id: Annotated[int | None, Query()] = None,
        name: Annotated[str | None, Query()] = None,
    ) -> JSONResponse:
        scoped = _scoped(
            request=request,
            repo=repo,
            settings_repo=settings_repo,
            plan_id=plan_id,
            name=name,
        )
        if isinstance(scoped, ExplainFailure):
            return _json(scoped)
        resolved_id, resolved_plan, result = scoped
        return _json(
            diagnostics_payload(
                plan_id=resolved_id,
                plan_name=resolved_plan.name,
                result=result,
            )
        )

    @web_app.get(API_RESULT_SERIES)
    def series(
        *,
        request: Request,
        repo: RepoDep,
        settings_repo: SettingsRepoDep,
        plan_id: Annotated[int | None, Query()] = None,
        name: Annotated[str | None, Query()] = None,
        series: Annotated[str | None, Query()] = None,
        month: Annotated[int | None, Query()] = None,
        percentile: Annotated[int | None, Query()] = None,
    ) -> JSONResponse:
        if series is None:
            return _json(
                ExplainFailure(
                    status_code=HTTP_BAD_REQUEST,
                    code=INVALID_QUERY,
                    message="series is required",
                )
            )
        invalid_series = validate_series(series)
        if invalid_series is not None:
            return _json(invalid_series)
        scoped = _scoped(
            request=request,
            repo=repo,
            settings_repo=settings_repo,
            plan_id=plan_id,
            name=name,
        )
        if isinstance(scoped, ExplainFailure):
            return _json(scoped)
        resolved_id, resolved_plan, result = scoped
        return _json(
            series_payload(
                plan_id=resolved_id,
                plan_name=resolved_plan.name,
                result=result,
                series=series,
                month=month,
                percentile=percentile,
            )
        )
