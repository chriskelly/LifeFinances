from __future__ import annotations

from dataclasses import dataclass

from core.models import Plan
from core.repository import PlanRepository, UnloadablePlan
from core.settings_repository import SettingsRepository

INVALID_QUERY = "invalid_query"
PLAN_NOT_FOUND = "plan_not_found"
AMBIGUOUS_PLAN = "ambiguous_plan"
PLAN_UNLOADABLE = "plan_unloadable"

HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_UNPROCESSABLE = 422


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
