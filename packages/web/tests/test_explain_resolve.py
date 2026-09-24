import sqlite3
from typing import cast

import pytest
from core.repository import PlanRepository, PlanSummary, UnloadablePlan
from core.settings_repository import SettingsRepository
from web.dependencies import SelectedPlan
from web.explain import (
    AMBIGUOUS_PLAN,
    HTTP_BAD_REQUEST,
    HTTP_CONFLICT,
    HTTP_NOT_FOUND,
    HTTP_UNPROCESSABLE,
    INVALID_QUERY,
    PLAN_NOT_FOUND,
    PLAN_UNLOADABLE,
    ApiError,
    PlanListItem,
    PlanRef,
    list_loadable_plans,
    resolve_plan,
)


def _insert_corrupt_plan(*, repo: PlanRepository) -> int:
    payload = "{not-valid-plan-json"
    conn = sqlite3.connect(repo.db_path)
    try:
        cur = conn.execute(
            "INSERT INTO plans (name, data) VALUES (?, ?)",
            ("Corrupt", payload),
        )
        conn.commit()
        plan_id = cur.lastrowid
    finally:
        conn.close()
    assert plan_id is not None
    return plan_id


def test_resolve_plan_rejects_both_identity_params(repo: PlanRepository) -> None:
    plan_name = "Only"
    plan_id, _ = repo.create(name=plan_name)

    with pytest.raises(ApiError) as raised:
        resolve_plan(plan_repo=repo, plan_id=plan_id, name=plan_name)

    assert raised.value.status_code == HTTP_BAD_REQUEST
    assert raised.value.code == INVALID_QUERY


def test_resolve_plan_rejects_neither_identity_param(repo: PlanRepository) -> None:
    with pytest.raises(ApiError) as raised:
        resolve_plan(plan_repo=repo, plan_id=None, name=None)

    assert raised.value.status_code == HTTP_BAD_REQUEST
    assert raised.value.code == INVALID_QUERY


def test_resolve_plan_rejects_blank_name(repo: PlanRepository) -> None:
    with pytest.raises(ApiError) as raised:
        resolve_plan(plan_repo=repo, plan_id=None, name="   ")

    assert raised.value.status_code == HTTP_BAD_REQUEST
    assert raised.value.code == INVALID_QUERY


def test_resolve_plan_by_exact_name(repo: PlanRepository) -> None:
    stored_name = "Exact Plan"
    plan_id, created = repo.create(name=stored_name)

    resolved = resolve_plan(plan_repo=repo, plan_id=None, name=stored_name)

    assert resolved == SelectedPlan(id=plan_id, plan=created)


def test_name_match_strips_query_and_stored_name(repo: PlanRepository) -> None:
    stored_name = "Base "
    plan_id, created = repo.create(name=stored_name)
    query = "Base"

    resolved = resolve_plan(plan_repo=repo, plan_id=None, name=query)

    assert resolved == SelectedPlan(id=plan_id, plan=created)


def test_name_match_is_case_sensitive(repo: PlanRepository) -> None:
    stored_name = "Base"
    repo.create(name=stored_name)

    with pytest.raises(ApiError) as raised:
        resolve_plan(plan_repo=repo, plan_id=None, name=stored_name.lower())

    assert raised.value.status_code == HTTP_NOT_FOUND
    assert raised.value.code == PLAN_NOT_FOUND


def test_stripped_name_collision_is_ambiguous(repo: PlanRepository) -> None:
    first_name = "Base"
    second_name = "Base "
    first_id, _ = repo.create(name=first_name)
    second_id, _ = repo.create(name=second_name)

    with pytest.raises(ApiError) as raised:
        resolve_plan(plan_repo=repo, plan_id=None, name=first_name)

    failure = raised.value
    assert failure.status_code == HTTP_CONFLICT
    assert failure.code == AMBIGUOUS_PLAN
    assert failure.candidates == (
        PlanRef(id=first_id, name=first_name),
        PlanRef(id=second_id, name=second_name),
    )


def test_resolve_plan_reports_unloadable_validation_message(
    repo: PlanRepository,
) -> None:
    corrupt_id = _insert_corrupt_plan(repo=repo)
    loaded = repo.load_plan(corrupt_id)
    assert isinstance(loaded, UnloadablePlan)

    with pytest.raises(ApiError) as raised:
        resolve_plan(plan_repo=repo, plan_id=corrupt_id, name=None)

    failure = raised.value
    assert failure.status_code == HTTP_UNPROCESSABLE
    assert failure.code == PLAN_UNLOADABLE
    assert failure.message == loaded.message


def test_name_resolution_ignores_unloadable_stored_names(
    repo: PlanRepository,
) -> None:
    query = "Ghost"
    conn = sqlite3.connect(repo.db_path)
    try:
        conn.execute(
            "INSERT INTO plans (name, data) VALUES (?, ?)",
            (f"{query} ", "{not-valid-plan-json"),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ApiError) as raised:
        resolve_plan(plan_repo=repo, plan_id=None, name=query)

    assert raised.value.status_code == HTTP_NOT_FOUND
    assert raised.value.code == PLAN_NOT_FOUND


def test_missing_plan_id_is_not_found(repo: PlanRepository) -> None:
    missing_id = 999_999

    with pytest.raises(ApiError) as raised:
        resolve_plan(plan_repo=repo, plan_id=missing_id, name=None)

    assert raised.value.status_code == HTTP_NOT_FOUND
    assert raised.value.code == PLAN_NOT_FOUND


def test_list_loadable_plans_skips_unloadable_and_marks_default(
    repo: PlanRepository,
) -> None:
    kept_name = "Kept"
    other_name = "Other"
    kept_id, _ = repo.create(name=kept_name)
    other_id, _ = repo.create(name=other_name)
    _insert_corrupt_plan(repo=repo)
    settings = SettingsRepository(db_path=repo.db_path)
    settings.save(settings.get().model_copy(update={"default_plan_id": kept_id}))

    listed = list_loadable_plans(plan_repo=repo, settings_repo=settings)

    assert listed == [
        PlanListItem(id=kept_id, name=kept_name, is_default=True),
        PlanListItem(id=other_id, name=other_name, is_default=False),
    ]


def test_api_error_body_includes_candidates_only() -> None:
    code = AMBIGUOUS_PLAN
    message = "pick one"
    candidates = (PlanRef(id=1, name="A"), PlanRef(id=2, name="B"))
    failure = ApiError(
        status_code=HTTP_CONFLICT,
        code=code,
        message=message,
        candidates=candidates,
    )

    body = failure.body()

    assert body["error"] == code
    assert body["message"] == message
    assert body["candidates"] == [
        {"id": item.id, "name": item.name} for item in candidates
    ]
    assert "allowed" not in body
    assert "min" not in body
    assert "max" not in body


def test_api_error_body_includes_allowed_range_without_candidates() -> None:
    code = INVALID_QUERY
    message = "bad request"
    allowed = ("month", "year")
    min_month = 1
    max_month = 600
    failure = ApiError(
        status_code=HTTP_BAD_REQUEST,
        code=code,
        message=message,
        allowed=allowed,
        month_bounds=(min_month, max_month),
    )

    body = failure.body()

    assert body["error"] == code
    assert body["message"] == message
    assert body["allowed"] == list(allowed)
    assert body["min"] == min_month
    assert body["max"] == max_month
    assert "candidates" not in body


def test_name_match_reports_unloadable_when_matched_row_will_not_load() -> None:
    stored_name = "Kept"
    plan_id = 7
    message = "row failed validation"

    class _ReloadUnloadable:
        def list_loadable(self) -> list[PlanSummary]:
            return [PlanSummary(id=plan_id, name=stored_name)]

        def load_plan(self, requested_id: int) -> UnloadablePlan:
            assert requested_id == plan_id
            return UnloadablePlan(id=requested_id, message=message)

    with pytest.raises(ApiError) as raised:
        resolve_plan(
            plan_repo=cast(PlanRepository, _ReloadUnloadable()),
            plan_id=None,
            name=stored_name,
        )

    failure = raised.value
    assert failure.status_code == HTTP_UNPROCESSABLE
    assert failure.code == PLAN_UNLOADABLE
    assert failure.message == message
