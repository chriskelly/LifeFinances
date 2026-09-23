import sqlite3

from core.repository import PlanRepository, UnloadablePlan
from core.settings_repository import SettingsRepository
from web.explain import (
    AMBIGUOUS_PLAN,
    HTTP_BAD_REQUEST,
    HTTP_CONFLICT,
    HTTP_NOT_FOUND,
    HTTP_UNPROCESSABLE,
    INVALID_QUERY,
    PLAN_NOT_FOUND,
    PLAN_UNLOADABLE,
    ExplainFailure,
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
    plan_id, _ = repo.create(name="Only")

    failure = resolve_plan(plan_repo=repo, plan_id=plan_id, name="Only")

    assert isinstance(failure, ExplainFailure)
    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == INVALID_QUERY


def test_resolve_plan_rejects_neither_identity_param(repo: PlanRepository) -> None:
    failure = resolve_plan(plan_repo=repo, plan_id=None, name=None)

    assert isinstance(failure, ExplainFailure)
    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == INVALID_QUERY


def test_resolve_plan_rejects_blank_name(repo: PlanRepository) -> None:
    failure = resolve_plan(plan_repo=repo, plan_id=None, name="   ")

    assert isinstance(failure, ExplainFailure)
    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == INVALID_QUERY


def test_resolve_plan_by_exact_name(repo: PlanRepository) -> None:
    stored_name = "Exact Plan"
    plan_id, created = repo.create(name=stored_name)

    resolved = resolve_plan(plan_repo=repo, plan_id=None, name=stored_name)

    assert resolved == (plan_id, created)


def test_name_match_strips_query_and_stored_name(repo: PlanRepository) -> None:
    stored_name = "Base "
    plan_id, created = repo.create(name=stored_name)
    query = "Base"

    resolved = resolve_plan(plan_repo=repo, plan_id=None, name=query)

    assert resolved == (plan_id, created)


def test_name_match_is_case_sensitive(repo: PlanRepository) -> None:
    stored_name = "Base"
    repo.create(name=stored_name)

    failure = resolve_plan(plan_repo=repo, plan_id=None, name=stored_name.lower())

    assert isinstance(failure, ExplainFailure)
    assert failure.status_code == HTTP_NOT_FOUND
    assert failure.code == PLAN_NOT_FOUND


def test_stripped_name_collision_is_ambiguous(repo: PlanRepository) -> None:
    first_name = "Base"
    second_name = "Base "
    first_id, _ = repo.create(name=first_name)
    second_id, _ = repo.create(name=second_name)

    failure = resolve_plan(plan_repo=repo, plan_id=None, name="Base")

    assert isinstance(failure, ExplainFailure)
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

    failure = resolve_plan(plan_repo=repo, plan_id=corrupt_id, name=None)

    assert isinstance(failure, ExplainFailure)
    assert failure.status_code == HTTP_UNPROCESSABLE
    assert failure.code == PLAN_UNLOADABLE
    assert failure.message == loaded.message


def test_missing_plan_id_is_not_found(repo: PlanRepository) -> None:
    missing_id = 999_999

    failure = resolve_plan(plan_repo=repo, plan_id=missing_id, name=None)

    assert isinstance(failure, ExplainFailure)
    assert failure.status_code == HTTP_NOT_FOUND
    assert failure.code == PLAN_NOT_FOUND


def test_list_loadable_plans_skips_unloadable_and_marks_default(
    repo: PlanRepository,
) -> None:
    kept_name = "Kept"
    kept_id, _ = repo.create(name=kept_name)
    _insert_corrupt_plan(repo=repo)
    settings = SettingsRepository(db_path=repo.db_path)
    settings.save(settings.get().model_copy(update={"default_plan_id": kept_id}))

    listed = list_loadable_plans(plan_repo=repo, settings_repo=settings)

    assert listed == [PlanListItem(id=kept_id, name=kept_name, is_default=True)]
