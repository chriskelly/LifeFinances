from datetime import date, datetime
from decimal import Decimal

from core.defaults import DEFAULT_PLAN_NAME, default_plan
from simulation.result import STUB_VERSION
from simulation.stub import run_simulation


def test_run_simulation_echo_reflects_plan_balance() -> None:
    fixed_today = date(2026, 6, 13)
    fixed_ran_at = datetime(2026, 6, 13, 12, 0, 0)
    expected_balance = Decimal("123456")
    plan = default_plan()
    plan.portfolio.current_savings_balance = expected_balance

    result = run_simulation(plan, today=fixed_today, ran_at=fixed_ran_at)

    assert result.echo["balance"] == expected_balance
    assert result.echo["plan_name"] == DEFAULT_PLAN_NAME
    assert result.stub_version == STUB_VERSION


def test_run_simulation_is_deterministic_for_fixed_clock() -> None:
    fixed_today = date(2026, 6, 13)
    fixed_ran_at = datetime(2026, 6, 13, 12, 0, 0)
    plan = default_plan()

    first = run_simulation(plan, today=fixed_today, ran_at=fixed_ran_at)
    second = run_simulation(plan, today=fixed_today, ran_at=fixed_ran_at)

    assert first == second
