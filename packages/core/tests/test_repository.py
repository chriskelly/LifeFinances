from __future__ import annotations

import sqlite3
from decimal import Decimal

from core.defaults import DEFAULT_PLAN_NAME, DEFAULT_SAVINGS_BALANCE
from core.repository import PlanRepository


def test_get_or_create_default_inserts_when_no_plans(repo: PlanRepository) -> None:
    plan_id, plan = repo.get_or_create_default()

    assert plan_id == 1
    assert plan.name == DEFAULT_PLAN_NAME
    assert plan.portfolio.current_savings_balance == DEFAULT_SAVINGS_BALANCE


def test_save_and_get_by_id_round_trip_preserves_balance(repo: PlanRepository) -> None:
    plan_id, plan = repo.get_or_create_default()
    expected_balance = Decimal("750000")

    plan.portfolio.current_savings_balance = expected_balance
    repo.save(plan_id, plan)
    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    assert loaded.portfolio.current_savings_balance == expected_balance


def test_get_or_create_default_returns_existing_without_insert(
    repo: PlanRepository,
) -> None:
    first_id, _ = repo.get_or_create_default()
    second_id, _ = repo.get_or_create_default()

    assert second_id == first_id
    conn = sqlite3.connect(repo.db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
    finally:
        conn.close()
    assert count == 1
