from __future__ import annotations

import json
import sqlite3
from datetime import date
from decimal import Decimal

from core.defaults import DEFAULT_PLAN_NAME, DEFAULT_SAVINGS_BALANCE
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from core.streams import CalendarMonthBoundary


def test_get_or_create_default_inserts_when_no_plans(repo: PlanRepository) -> None:
    plan_id, plan = repo.get_or_create_default()

    assert plan_id == 1
    assert plan.name == DEFAULT_PLAN_NAME
    assert plan.portfolio.current_savings_balance == DEFAULT_SAVINGS_BALANCE
    assert SettingsRepository(db_path=repo.db_path).get().default_plan_id == plan_id


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


def test_get_by_id_coerces_null_job_and_stream_starts_to_today(
    repo: PlanRepository,
) -> None:
    plan_id, plan = repo.get_or_create_default()
    injected_today = date(2026, 7, 15)
    expected_start = CalendarMonthBoundary(
        year=injected_today.year, month=injected_today.month
    )
    payload = json.loads(plan.model_dump_json())
    payload["household"]["person1"]["jobs"] = [
        {"annual_income": "120000", "start": None}
    ]
    payload["manual_income_streams"] = [{"monthly_amount": "500", "start": None}]
    conn = sqlite3.connect(repo.db_path)
    try:
        conn.execute(
            "UPDATE plans SET data = ? WHERE id = ?",
            (json.dumps(payload), plan_id),
        )
        conn.commit()
    finally:
        conn.close()

    loaded = repo.get_by_id(plan_id, today=injected_today)

    assert loaded is not None
    assert loaded.household.person1.jobs[0].start == expected_start
    assert loaded.manual_income_streams[0].start == expected_start

    repo.save(plan_id, loaded)
    round_tripped = repo.get_by_id(plan_id, today=date(2099, 1, 1))
    assert round_tripped is not None
    assert round_tripped.household.person1.jobs[0].start == expected_start
    assert round_tripped.manual_income_streams[0].start == expected_start
