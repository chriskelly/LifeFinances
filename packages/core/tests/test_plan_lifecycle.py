from __future__ import annotations

from core.defaults import DEFAULT_PLAN_NAME
from core.plan_names import UNTITLED_PLAN_BASE
from core.repository import PlanRepository, PlanSummary
from core.settings_repository import SettingsRepository


def test_list_returns_summaries_ordered_by_id(repo: PlanRepository) -> None:
    first_name = "Alpha"
    second_name = "Beta"
    first_id, first = repo.create(name=first_name)
    second_id, second = repo.create(name=second_name)

    summaries = repo.list()

    assert summaries == [
        PlanSummary(id=first_id, name=first.name),
        PlanSummary(id=second_id, name=second.name),
    ]
    assert first.name == first_name
    assert second.name == second_name


def test_create_inserts_blank_default_plan_with_given_name(
    repo: PlanRepository,
) -> None:
    expected_name = UNTITLED_PLAN_BASE
    plan_id, plan = repo.create(name=expected_name)

    loaded = repo.get_by_id(plan_id)
    assert loaded is not None
    assert loaded.name == expected_name
    assert plan.name == expected_name


def test_ensure_bootstrap_creates_plan_and_sets_default_when_empty(
    db_path,
) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)

    plan_id, plan = plans.ensure_bootstrap(settings_repo=settings)

    assert plan_id >= 1
    assert settings.get().default_plan_id == plan_id
    assert plans.get_by_id(plan_id) is not None
    assert plan.name == DEFAULT_PLAN_NAME


def test_ensure_bootstrap_is_idempotent_when_plans_exist(db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    first_id, _ = plans.ensure_bootstrap(settings_repo=settings)

    second_id, _ = plans.ensure_bootstrap(settings_repo=settings)

    assert second_id == first_id
    assert len(plans.list()) == 1
