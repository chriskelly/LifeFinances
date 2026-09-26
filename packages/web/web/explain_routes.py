from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from web.dependencies import (
    DbPathDep,
    RepoDep,
    SelectedPlan,
    SettingsDep,
    SettingsRepoDep,
)
from web.explain import (
    DB_NOT_INITIALIZED,
    DB_NOT_INITIALIZED_MESSAGE,
    HTTP_BAD_REQUEST,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_UNPROCESSABLE,
    INVALID_QUERY,
    SIMULATION_FAILED,
    ApiError,
    ScopedResult,
    diagnostics_payload,
    list_loadable_plans,
    require_known_series,
    resolve_plan,
    series_payload,
    summary_payload,
)
from web.routes import (
    API_PLAN,
    API_PLANS,
    API_RESULT_DIAGNOSTICS,
    API_RESULT_SERIES,
    API_RESULT_SUMMARY,
)
from web.simulation_cache import get_or_run_simulation


def require_initialized_database(db_path: DbPathDep) -> None:
    if not db_path.exists():
        raise ApiError(
            status_code=HTTP_SERVICE_UNAVAILABLE,
            code=DB_NOT_INITIALIZED,
            message=DB_NOT_INITIALIZED_MESSAGE,
        )


def require_api_plan(
    repo: RepoDep,
    plan_id: Annotated[int | None, Query()] = None,
    name: Annotated[str | None, Query()] = None,
) -> SelectedPlan:
    return resolve_plan(plan_repo=repo, plan_id=plan_id, name=name)


ApiPlanDep = Annotated[SelectedPlan, Depends(require_api_plan)]


def require_api_result(
    request: Request,
    selected: ApiPlanDep,
    settings: SettingsDep,
) -> ScopedResult:
    try:
        result = get_or_run_simulation(
            request.app,
            plan_id=selected.id,
            plan=selected.plan,
            settings=settings,
        )
    except Exception as exc:
        raise ApiError(
            status_code=HTTP_UNPROCESSABLE,
            code=SIMULATION_FAILED,
            message=str(exc),
        ) from exc
    return ScopedResult(plan_id=selected.id, plan=selected.plan, result=result)


ApiResultDep = Annotated[ScopedResult, Depends(require_api_result)]


def require_series(
    series: Annotated[str | None, Query()] = None,
) -> str:
    if series is None:
        raise ApiError(
            status_code=HTTP_BAD_REQUEST,
            code=INVALID_QUERY,
            message="series is required",
        )
    return require_known_series(series)


SeriesDep = Annotated[str, Depends(require_series)]


def register_explain_routes(web_app: FastAPI) -> None:
    @web_app.exception_handler(ApiError)
    def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        del request
        return JSONResponse(status_code=exc.status_code, content=exc.body())

    router = APIRouter(dependencies=[Depends(require_initialized_database)])
    _register_plan_routes(router)
    _register_result_routes(router)
    web_app.include_router(router)


def _register_plan_routes(router: APIRouter) -> None:
    @router.get(API_PLANS)
    def plans(*, repo: RepoDep, settings_repo: SettingsRepoDep) -> dict[str, object]:
        listed = list_loadable_plans(plan_repo=repo, settings_repo=settings_repo)
        return {"plans": [asdict(item) for item in listed]}

    @router.get(API_PLAN)
    def plan(*, selected: ApiPlanDep) -> dict[str, object]:
        return {
            "plan_id": selected.id,
            "name": selected.plan.name,
            "plan": selected.plan.model_dump(mode="json"),
        }


def _register_result_routes(router: APIRouter) -> None:
    @router.get(API_RESULT_SUMMARY)
    def summary(*, scoped: ApiResultDep) -> dict[str, object]:
        return summary_payload(scoped)

    @router.get(API_RESULT_DIAGNOSTICS)
    def diagnostics(*, scoped: ApiResultDep) -> dict[str, object]:
        return diagnostics_payload(scoped)

    @router.get(API_RESULT_SERIES)
    def series(
        *,
        series: SeriesDep,
        scoped: ApiResultDep,
        month: Annotated[int | None, Query()] = None,
        percentile: Annotated[int | None, Query()] = None,
    ) -> dict[str, object]:
        return series_payload(
            scoped=scoped,
            series=series,
            month=month,
            percentile=percentile,
        )
