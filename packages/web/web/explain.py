from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from core.models import Plan
from core.repository import PlanRepository, UnloadablePlan
from core.settings_repository import SettingsRepository
from simulation.diagnostics import DIAGNOSTICS_ARRAY_FIELDS
from simulation.result import (
    HORIZON_ARRAY_FIELDS,
    PUBLIC_ARRAY_FIELDS,
    RAW_ARRAY_FIELDS,
    SimulationResult,
)

from web import spending_summary
from web.calendar_months import month_labels
from web.dependencies import SelectedPlan

INVALID_QUERY = "invalid_query"
DB_NOT_INITIALIZED = "db_not_initialized"
DB_NOT_INITIALIZED_MESSAGE = "No database found. Run: uv run python scripts/init_db.py"
PLAN_NOT_FOUND = "plan_not_found"
AMBIGUOUS_PLAN = "ambiguous_plan"
PLAN_UNLOADABLE = "plan_unloadable"
UNKNOWN_SERIES = "unknown_series"
UNKNOWN_FIELD = "unknown_field"
UNKNOWN_PERCENTILE = "unknown_percentile"
PERCENTILE_NOT_APPLICABLE = "percentile_not_applicable"
MONTH_OUT_OF_RANGE = "month_out_of_range"
INVALID_RANGE = "invalid_range"
SIMULATION_FAILED = "simulation_failed"

HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_UNPROCESSABLE = 422
HTTP_SERVICE_UNAVAILABLE = 503


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
class ScopedResult:
    plan_id: int
    plan: Plan
    result: SimulationResult


@dataclass
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    candidates: tuple[PlanRef, ...] = ()
    allowed: tuple[str | int, ...] = ()
    month_bounds: tuple[int, int] | None = None

    def body(self) -> dict[str, object]:
        payload: dict[str, object] = {"error": self.code, "message": self.message}
        if self.candidates:
            payload["candidates"] = [
                {"id": item.id, "name": item.name} for item in self.candidates
            ]
        if self.allowed:
            payload["allowed"] = list(self.allowed)
        if self.month_bounds is not None:
            payload["min"], payload["max"] = self.month_bounds
        return payload


def summary_payload(scoped: ScopedResult) -> dict[str, object]:
    spending = spending_summary.from_result(scoped.result)
    result = scoped.result
    return {
        "plan_id": scoped.plan_id,
        "name": scoped.plan.name,
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
    scoped: ScopedResult,
    *,
    month: int | None = None,
    fields: Sequence[str] | None = None,
) -> dict[str, object]:
    """Build the diagnostics JSON.

    ``fields`` accepts raw query tokens or an already-resolved canonical tuple;
    it re-resolves so direct callers get the same 400 ``unknown_field`` and so
    fields are validated before ``month`` on every path.
    """
    result = scoped.result
    diagnostics = result.diagnostics
    resolved_fields = resolve_diagnostics_fields(fields)
    require_month(
        month=month, horizon_months=result.horizon_months, subject="diagnostics"
    )
    payload: dict[str, object] = {
        "plan_id": scoped.plan_id,
        "name": scoped.plan.name,
        "legacy_stock_allocation": diagnostics.legacy_stock_allocation,
    }
    if month is not None:
        payload["month"] = month
    first, last = _month_span(month=month, horizon_months=result.horizon_months)
    for field in resolved_fields:
        payload[field] = _month_slice(
            values=getattr(diagnostics, field), first=first, last=last
        )
    return payload


def resolve_diagnostics_fields(fields: Sequence[str] | None) -> tuple[str, ...]:
    """Resolve requested diagnostics arrays into canonical source order.

    Accepts both repeated query values and comma-separated tokens. Missing,
    empty, and all-blank input means every array field. Raises ApiError for an
    unknown name so the route can reject it before running a simulation.
    """
    if fields is None:
        return DIAGNOSTICS_ARRAY_FIELDS
    if isinstance(fields, str):
        fields = [fields]
    requested: set[str] = set()
    for raw in fields:
        for token in raw.split(","):
            name = token.strip()
            if not name:
                continue
            if name not in DIAGNOSTICS_ARRAY_FIELDS:
                raise ApiError(
                    status_code=HTTP_BAD_REQUEST,
                    code=UNKNOWN_FIELD,
                    message=f"Unknown field {name}",
                    allowed=DIAGNOSTICS_ARRAY_FIELDS,
                )
            requested.add(name)
    if not requested:
        return DIAGNOSTICS_ARRAY_FIELDS
    return tuple(field for field in DIAGNOSTICS_ARRAY_FIELDS if field in requested)


def require_month(
    *,
    month: int | None,
    horizon_months: int,
    subject: str,
) -> None:
    """Reject an out-of-range month; series and diagnostics share this guard.

    A None month is a no-op. Otherwise the month must be a zero-based index in
    ``[0, horizon_months - 1]``. A horizon below one month reports the range
    error without bounds, because there is no valid index to advertise.
    """
    if month is None:
        return
    bounds = _month_bounds(horizon_months=horizon_months, subject=subject)
    _require_in_bounds(param="month", value=month, bounds=bounds)


def _month_bounds(*, horizon_months: int, subject: str) -> tuple[int, int]:
    """Inclusive zero-based month bounds, or an error when there are no months."""
    if horizon_months < 1:
        raise ApiError(
            status_code=HTTP_BAD_REQUEST,
            code=MONTH_OUT_OF_RANGE,
            message=f"{subject} has no months",
        )
    return 0, horizon_months - 1


def _month_span(*, month: int | None, horizon_months: int) -> tuple[int, int]:
    """Inclusive span for one month, or for the whole horizon.

    An empty horizon yields ``(0, -1)`` so slicing produces empty lists rather
    than an error, matching the no-range payload.
    """
    return (month, month) if month is not None else (0, horizon_months - 1)


def require_month_selection(
    *,
    month: int | None,
    month_from: int | None,
    month_to: int | None,
) -> None:
    """Reject ``month`` combined with a range bound, or an inverted range.

    Both checks are horizon-independent, so routes can reject them before
    running a simulation.
    """
    if month is not None and (month_from is not None or month_to is not None):
        raise ApiError(
            status_code=HTTP_BAD_REQUEST,
            code=INVALID_QUERY,
            message="Provide either month or a month_from/month_to range, not both",
        )
    _require_month_range_order(month_from=month_from, month_to=month_to)


def _require_month_range_order(*, month_from: int | None, month_to: int | None) -> None:
    """Reject an inverted range."""
    if month_from is not None and month_to is not None and month_from > month_to:
        raise ApiError(
            status_code=HTTP_BAD_REQUEST,
            code=INVALID_RANGE,
            message="month_from must be less than or equal to month_to",
        )


def require_month_range(
    *,
    month_from: int | None,
    month_to: int | None,
    horizon_months: int,
    subject: str,
) -> tuple[int, int]:
    """Resolve optional inclusive range bounds against the horizon.

    A missing bound defaults to the first or last month. Both the range order
    and each supplied bound are validated, so a direct payload caller and the
    route dependency reject the same requests.
    """
    _require_month_range_order(month_from=month_from, month_to=month_to)
    bounds = _month_bounds(horizon_months=horizon_months, subject=subject)
    if month_from is not None:
        _require_in_bounds(param="month_from", value=month_from, bounds=bounds)
    if month_to is not None:
        _require_in_bounds(param="month_to", value=month_to, bounds=bounds)
    first, last = bounds
    return (
        first if month_from is None else month_from,
        last if month_to is None else month_to,
    )


def _require_in_bounds(*, param: str, value: int, bounds: tuple[int, int]) -> None:
    first, last = bounds
    if not first <= value <= last:
        raise ApiError(
            status_code=HTTP_BAD_REQUEST,
            code=MONTH_OUT_OF_RANGE,
            message=f"{param} must be between {first} and {last} inclusive",
            month_bounds=bounds,
        )


def _month_slice(*, values: np.ndarray, first: int, last: int) -> list[float]:
    """Inclusive month slice as a list; ``last < first`` yields an empty list."""
    return values[first : last + 1].tolist()


def series_payload(
    *,
    scoped: ScopedResult,
    series: str,
    month: int | None,
    percentile: int | None,
    month_from: int | None = None,
    month_to: int | None = None,
) -> dict[str, object]:
    require_known_series(series)
    require_month_selection(month=month, month_from=month_from, month_to=month_to)
    result = scoped.result
    values = getattr(result, series)
    require_month(month=month, horizon_months=result.horizon_months, subject="series")
    requested_range = month_from is not None or month_to is not None
    if requested_range:
        first, last = require_month_range(
            month_from=month_from,
            month_to=month_to,
            horizon_months=result.horizon_months,
            subject="series",
        )
    else:
        first, last = _month_span(month=month, horizon_months=result.horizon_months)
    if series in RAW_ARRAY_FIELDS:
        rows = _percentile_rows(
            result=result,
            values=values,
            first=first,
            last=last,
            percentile=percentile,
        )
    elif series in HORIZON_ARRAY_FIELDS:
        rows = _horizon_rows(
            values=values,
            first=first,
            last=last,
            percentile=percentile,
        )
    else:
        raise ApiError(
            status_code=HTTP_BAD_REQUEST,
            code=UNKNOWN_SERIES,
            message=f"Unknown series {series}",
            allowed=PUBLIC_ARRAY_FIELDS,
        )
    payload: dict[str, object] = {
        "plan_id": scoped.plan_id,
        "name": scoped.plan.name,
        "series": series,
        "month": month,
    }
    if requested_range:
        payload["month_from"] = first
        payload["month_to"] = last
    payload["labels"] = month_labels(result.start_month, result.horizon_months)[
        first : last + 1
    ]
    payload["rows"] = rows
    return payload


def require_known_series(series: str) -> str:
    if series in PUBLIC_ARRAY_FIELDS:
        return series
    raise ApiError(
        status_code=HTTP_BAD_REQUEST,
        code=UNKNOWN_SERIES,
        message=f"Unknown series {series}",
        allowed=PUBLIC_ARRAY_FIELDS,
    )


def _percentile_rows(
    *,
    result: SimulationResult,
    values: np.ndarray,
    first: int,
    last: int,
    percentile: int | None,
) -> list[dict[str, object]]:
    if percentile is None:
        row_indexes = range(len(result.percentiles))
    else:
        try:
            row_indexes = (result.percentiles.index(percentile),)
        except ValueError:
            raise ApiError(
                status_code=HTTP_BAD_REQUEST,
                code=UNKNOWN_PERCENTILE,
                message=f"Unknown percentile {percentile}",
                allowed=tuple(result.percentiles),
            ) from None
    return [
        {
            "percentile": result.percentiles[row_index],
            "values": _month_slice(values=values[row_index], first=first, last=last),
        }
        for row_index in row_indexes
    ]


def _horizon_rows(
    *,
    values: np.ndarray,
    first: int,
    last: int,
    percentile: int | None,
) -> list[dict[str, object]]:
    if percentile is not None:
        raise ApiError(
            status_code=HTTP_BAD_REQUEST,
            code=PERCENTILE_NOT_APPLICABLE,
            message="percentile does not apply to this series",
        )
    serialized = _month_slice(values=values, first=first, last=last)
    return [{"percentile": None, "values": serialized}]


def list_loadable_plans(
    *, plan_repo: PlanRepository, settings_repo: SettingsRepository
) -> list[PlanListItem]:
    default_id = settings_repo.get().default_plan_id
    return [
        PlanListItem(
            id=summary.id,
            name=summary.name,
            is_default=summary.id == default_id,
        )
        for summary in plan_repo.list_loadable()
    ]


def resolve_plan(
    *,
    plan_repo: PlanRepository,
    plan_id: int | None,
    name: str | None,
) -> SelectedPlan:
    if (plan_id is None) == (name is None):
        raise ApiError(
            status_code=HTTP_BAD_REQUEST,
            code=INVALID_QUERY,
            message="Provide exactly one of plan_id or name",
        )
    if plan_id is not None:
        return _resolve_id(plan_repo=plan_repo, plan_id=plan_id)
    assert name is not None
    return _resolve_name(plan_repo=plan_repo, name=name)


def _resolve_id(*, plan_repo: PlanRepository, plan_id: int) -> SelectedPlan:
    loaded = plan_repo.load_plan(plan_id)
    if loaded is None:
        raise ApiError(
            status_code=HTTP_NOT_FOUND,
            code=PLAN_NOT_FOUND,
            message=f"No plan with id {plan_id}",
        )
    if isinstance(loaded, UnloadablePlan):
        raise ApiError(
            status_code=HTTP_UNPROCESSABLE,
            code=PLAN_UNLOADABLE,
            message=loaded.message,
        )
    return SelectedPlan(id=plan_id, plan=loaded)


def _resolve_name(*, plan_repo: PlanRepository, name: str) -> SelectedPlan:
    query = name.strip()
    if not query:
        raise ApiError(
            status_code=HTTP_BAD_REQUEST,
            code=INVALID_QUERY,
            message="name must be non-empty",
        )
    loadable = plan_repo.list_loadable()
    matches = [summary for summary in loadable if summary.name.strip() == query]
    if not matches:
        raise ApiError(
            status_code=HTTP_NOT_FOUND,
            code=PLAN_NOT_FOUND,
            message=f"No loadable plan named {query}",
        )
    if len(matches) > 1:
        raise ApiError(
            status_code=HTTP_CONFLICT,
            code=AMBIGUOUS_PLAN,
            message="More than one plan matches that name",
            candidates=tuple(
                PlanRef(id=summary.id, name=summary.name) for summary in matches
            ),
        )
    summary = matches[0]
    loaded = plan_repo.load_plan(summary.id)
    if isinstance(loaded, UnloadablePlan):
        raise ApiError(
            status_code=HTTP_UNPROCESSABLE,
            code=PLAN_UNLOADABLE,
            message=loaded.message,
        )
    if not isinstance(loaded, Plan):
        raise ApiError(
            status_code=HTTP_NOT_FOUND,
            code=PLAN_NOT_FOUND,
            message=f"No loadable plan named {query}",
        )
    return SelectedPlan(id=summary.id, plan=loaded)
