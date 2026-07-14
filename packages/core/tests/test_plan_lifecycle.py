from __future__ import annotations

from decimal import Decimal

import pytest
from core.defaults import DEFAULT_PLAN_NAME
from core.plan_names import UNTITLED_PLAN_BASE, copy_plan_name
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


def test_ensure_bootstrap_repairs_orphan_default_plan_id(db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    first_id, _ = plans.create(name="Alpha")
    plans.create(name="Beta")
    stale_default_id = 999_999

    settings.save(
        settings.get().model_copy(update={"default_plan_id": stale_default_id})
    )

    resolved_id, _ = plans.ensure_bootstrap(settings_repo=settings)

    assert resolved_id == first_id
    assert settings.get().default_plan_id == first_id


def test_ensure_bootstrap_honors_valid_multi_plan_default(db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plans.create(name="Alpha")
    second_id, _ = plans.create(name="Beta")

    settings.save(settings.get().model_copy(update={"default_plan_id": second_id}))

    resolved_id, _ = plans.ensure_bootstrap(settings_repo=settings)

    assert resolved_id == second_id
    assert settings.get().default_plan_id == second_id


def test_duplicate_copies_json_and_assigns_copy_name(repo: PlanRepository) -> None:
    source_name = "Base"
    source_id, source = repo.create(name=source_name)
    expected_balance = Decimal("123456")
    source.portfolio.current_savings_balance = expected_balance
    repo.save(source_id, source)
    expected_copy_name = copy_plan_name(
        original_name=source_name, existing=[source_name]
    )

    new_id, duplicated = repo.duplicate(source_id)

    assert new_id != source_id
    assert duplicated.name == expected_copy_name
    assert duplicated.portfolio.current_savings_balance == expected_balance
    reloaded_source = repo.get_by_id(source_id)
    assert reloaded_source is not None
    assert reloaded_source.portfolio.current_savings_balance == expected_balance


def test_rename_updates_column_and_json(repo: PlanRepository) -> None:
    plan_id, _ = repo.create(name="Old")
    expected_name = "New Name"

    repo.rename(plan_id, name=expected_name)

    loaded = repo.get_by_id(plan_id)
    assert loaded is not None
    assert loaded.name == expected_name
    assert repo.list()[0].name == expected_name


def test_rename_rejects_blank_name(repo: PlanRepository) -> None:
    plan_id, _ = repo.create(name="Keep")
    with pytest.raises(ValueError, match="name"):
        repo.rename(plan_id, name="   ")


def test_delete_removes_plan(repo: PlanRepository) -> None:
    keep_id, _ = repo.create(name="Keep")
    drop_id, _ = repo.create(name="Drop")

    repo.delete(drop_id)

    assert repo.get_by_id(drop_id) is None
    assert [s.id for s in repo.list()] == [keep_id]


def test_delete_refuses_last_plan(repo: PlanRepository) -> None:
    only_id, _ = repo.create(name="Only")
    with pytest.raises(ValueError, match="last"):
        repo.delete(only_id)
    assert len(repo.list()) == 1
