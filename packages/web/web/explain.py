from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from core.models import AppSettings, Plan
from core.repository import PlanRepository, UnloadablePlan
from core.settings_repository import SettingsRepository
from fastapi import FastAPI
from simulation.diagnostics import DIAGNOSTICS_ARRAY_FIELDS
from simulation.result import PUBLIC_ARRAY_FIELDS, RAW_ARRAY_FIELDS, SimulationResult
from simulation.stub import run_simulation

from web import spending_summary
from web.simulation_cache import get_or_run_simulation

logger = logging.getLogger(__name__)

INVALID_QUERY = "invalid_query"
DB_NOT_INITIALIZED = "db_not_initialized"
DB_NOT_INITIALIZED_MESSAGE = "No database found. Run: uv run python scripts/init_db.py"
PLAN_NOT_FOUND = "plan_not_found"
AMBIGUOUS_PLAN = "ambiguous_plan"
PLAN_UNLOADABLE = "plan_unloadable"
UNKNOWN_SERIES = "unknown_series"
UNKNOWN_PERCENTILE = "unknown_percentile"
PERCENTILE_NOT_APPLICABLE = "percentile_not_applicable"
MONTH_OUT_OF_RANGE = "month_out_of_range"
SIMULATION_FAILED = "simulation_failed"

HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_UNPROCESSABLE = 422
HTTP_SERVICE_UNAVAILABLE = 503


def load_cached_result(
    *,
    app: FastAPI,
    plan_id: int,
    plan: Plan,
    settings: AppSettings,
) -> SimulationResult | ExplainFailure:
    try:
        return get_or_run_simulation(
            app,
            plan_id=plan_id,
            plan=plan,
            fred_api_key=settings.fred_api_key,
            eod_api_key=settings.eod_api_key,
            run=run_simulation,
        )
    except Exception as exc:
        logger.exception("Simulation failed for plan_id=%s", plan_id)
        return ExplainFailure(
            status_code=HTTP_UNPROCESSABLE,
            code=SIMULATION_FAILED,
            message=str(exc),
        )


@dataclass(frozen=True)
class PlanRef:
    id: int
    name: str


@dataclass(frozen=True)
class PlanListItem:
    id: int
    name: str
    is_default: bool


@dataclass(frozen=True)
class ExplainFailure:
    status_code: int
    code: str
    message: str
    candidates: tuple[PlanRef, ...] = ()
    allowed: tuple[object, ...] = ()
    min_month: int | None = None
    max_month: int | None = None

    def body(self) -> dict[str, object]:
        payload: dict[str, object] = {"error": self.code, "message": self.message}
        if self.candidates:
            payload["candidates"] = [
                {"id": item.id, "name": item.name} for item in self.candidates
            ]
        if self.allowed:
            payload["allowed"] = list(self.allowed)
        if self.min_month is not None and self.max_month is not None:
            payload["min"] = self.min_month
            payload["max"] = self.max_month
        return payload


def summary_payload(
    *, plan_id: int, plan_name: str, result: SimulationResult
) -> dict[str, object]:
    spending = spending_summary.from_result(result)
    return {
        "plan_id": plan_id,
        "name": plan_name,
        "ran_at": result.ran_at.isoformat(),
        "horizon_months": result.horizon_months,
        "num_runs": result.num_runs,
        "percentiles": list(result.percentiles),
        "start_month": list(result.start_month),
        "num_runs_insufficient": result.num_runs_insufficient,
        "resolved_assumptions": result.resolved_assumptions.model_dump(mode="json"),
        "spending": {
            "initial": spending.initial,
            "worst_case": spending.worst_case,
        },
    }


def diagnostics_payload(
    *, plan_id: int, plan_name: str, result: SimulationResult
) -> dict[str, object]:
    diagnostics = result.diagnostics
    payload: dict[str, object] = {
        "plan_id": plan_id,
        "name": plan_name,
        "legacy_stock_allocation": diagnostics.legacy_stock_allocation,
    }
    for field in DIAGNOSTICS_ARRAY_FIELDS:
        payload[field] = getattr(diagnostics, field).tolist()
    return payload


def series_payload(
    *,
    plan_id: int,
    plan_name: str,
    result: SimulationResult,
    series: str,
    month: int | None,
    percentile: int | None,
) -> dict[str, object] | ExplainFailure:
    invalid_series = validate_series(series)
    if invalid_series is not None:
        return invalid_series
    values = getattr(result, series)
    if month is not None and not 0 <= month < result.horizon_months:
        last = result.horizon_months - 1
        return ExplainFailure(
            status_code=HTTP_BAD_REQUEST,
            code=MONTH_OUT_OF_RANGE,
            message=f"month must be between 0 and {last} inclusive",
            min_month=0,
            max_month=last,
        )
    if series in RAW_ARRAY_FIELDS:
        rows = _percentile_rows(
            result=result,
            values=values,
            month=month,
            percentile=percentile,
        )
    else:
        rows = _horizon_rows(
            values=values,
            month=month,
            percentile=percentile,
        )
    if isinstance(rows, ExplainFailure):
        return rows
    return {
        "plan_id": plan_id,
        "name": plan_name,
        "series": series,
        "month": month,
        "rows": rows,
    }


def validate_series(series: str) -> ExplainFailure | None:
    if series in PUBLIC_ARRAY_FIELDS:
        return None
    return ExplainFailure(
        status_code=HTTP_BAD_REQUEST,
        code=UNKNOWN_SERIES,
        message=f"Unknown series {series}",
        allowed=PUBLIC_ARRAY_FIELDS,
    )


def _percentile_rows(
    *,
    result: SimulationResult,
    values: np.ndarray,
    month: int | None,
    percentile: int | None,
) -> list[dict[str, object]] | ExplainFailure:
    if percentile is None:
        row_indexes = range(len(result.percentiles))
    else:
        try:
            row_indexes = (result.percentiles.index(percentile),)
        except ValueError:
            return ExplainFailure(
                status_code=HTTP_BAD_REQUEST,
                code=UNKNOWN_PERCENTILE,
                message=f"Unknown percentile {percentile}",
                allowed=tuple(result.percentiles),
            )
    return [
        {
            "percentile": result.percentiles[row_index],
            "values": (
                values[row_index].tolist()
                if month is None
                else [values[row_index, month]]
            ),
        }
        for row_index in row_indexes
    ]


def _horizon_rows(
    *,
    values: np.ndarray,
    month: int | None,
    percentile: int | None,
) -> list[dict[str, object]] | ExplainFailure:
    if percentile is not None:
        return ExplainFailure(
            status_code=HTTP_BAD_REQUEST,
            code=PERCENTILE_NOT_APPLICABLE,
            message="percentile does not apply to this series",
        )
    serialized = values.tolist() if month is None else [values[month]]
    return [{"percentile": None, "values": serialized}]


def list_loadable_plans(
    *, plan_repo: PlanRepository, settings_repo: SettingsRepository
) -> list[PlanListItem]:
    loadable = plan_repo.loadable_ids()
    default_id = settings_repo.get().default_plan_id
    return [
        PlanListItem(
            id=summary.id,
            name=summary.name,
            is_default=summary.id == default_id,
        )
        for summary in plan_repo.list()
        if summary.id in loadable
    ]


def resolve_plan(
    *,
    plan_repo: PlanRepository,
    plan_id: int | None,
    name: str | None,
) -> tuple[int, Plan] | ExplainFailure:
    if (plan_id is None) == (name is None):
        return ExplainFailure(
            status_code=HTTP_BAD_REQUEST,
            code=INVALID_QUERY,
            message="Provide exactly one of plan_id or name",
        )
    if plan_id is not None:
        return _resolve_id(plan_repo=plan_repo, plan_id=plan_id)
    assert name is not None
    return _resolve_name(plan_repo=plan_repo, name=name)


def _resolve_id(
    *, plan_repo: PlanRepository, plan_id: int
) -> tuple[int, Plan] | ExplainFailure:
    loaded = plan_repo.load_plan(plan_id)
    if loaded is None:
        return ExplainFailure(
            status_code=HTTP_NOT_FOUND,
            code=PLAN_NOT_FOUND,
            message=f"No loadable plan with id {plan_id}",
        )
    if isinstance(loaded, UnloadablePlan):
        return ExplainFailure(
            status_code=HTTP_UNPROCESSABLE,
            code=PLAN_UNLOADABLE,
            message=loaded.message,
        )
    return plan_id, loaded


def _resolve_name(
    *, plan_repo: PlanRepository, name: str
) -> tuple[int, Plan] | ExplainFailure:
    query = name.strip()
    if not query:
        return ExplainFailure(
            status_code=HTTP_BAD_REQUEST,
            code=INVALID_QUERY,
            message="name must be non-empty",
        )
    loadable = plan_repo.loadable_ids()
    matches = [
        summary
        for summary in plan_repo.list()
        if summary.id in loadable and summary.name.strip() == query
    ]
    if not matches:
        return ExplainFailure(
            status_code=HTTP_NOT_FOUND,
            code=PLAN_NOT_FOUND,
            message=f"No loadable plan named {query}",
        )
    if len(matches) > 1:
        return ExplainFailure(
            status_code=HTTP_CONFLICT,
            code=AMBIGUOUS_PLAN,
            message="More than one plan matches that name",
            candidates=tuple(
                PlanRef(id=summary.id, name=summary.name) for summary in matches
            ),
        )
    summary = matches[0]
    loaded = plan_repo.load_plan(summary.id)
    if not isinstance(loaded, Plan):
        return ExplainFailure(
            status_code=HTTP_NOT_FOUND,
            code=PLAN_NOT_FOUND,
            message=f"No loadable plan named {query}",
        )
    return summary.id, loaded
