from __future__ import annotations

from datetime import date, datetime

from core.models import PersonHousehold, Plan

from simulation.horizon import horizon_months
from simulation.result import SimulationResult


def age_years(person: PersonHousehold, *, today: date) -> int:
    birthday_not_yet = (today.month, today.day) < (person.birth_month, 1)
    return today.year - person.birth_year - (1 if birthday_not_yet else 0)


def run_simulation(
    plan: Plan,
    *,
    percentiles: list[int] | None = None,
    today: date | None = None,
    ran_at: datetime | None = None,
) -> SimulationResult:
    today = today or date.today()
    ran_at = ran_at or datetime.now()
    _ = percentiles  # reserved for future API
    household = plan.household
    return SimulationResult(
        ran_at=ran_at,
        horizon_months=horizon_months(plan, today=today),
        echo={
            "balance": plan.portfolio.current_savings_balance,
            "person1_age_years": age_years(household.person1, today=today),
            "person2_age_years": age_years(household.person2, today=today),
            "plan_name": plan.name,
        },
    )
