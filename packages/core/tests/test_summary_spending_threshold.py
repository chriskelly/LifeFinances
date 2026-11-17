from __future__ import annotations

from decimal import Decimal

import pytest
from core.defaults import default_plan
from core.models import Plan
from core.repository import PlanRepository
from pydantic import ValidationError


def _plan_with(value: Decimal | None) -> Plan:
    data = default_plan().model_dump()
    data["summary_spending_threshold"] = value
    return Plan.model_validate(data)


def test_summary_spending_threshold_defaults_to_none() -> None:
    assert default_plan().summary_spending_threshold is None


@pytest.mark.parametrize("value", [None, Decimal(0), Decimal("12000")])
def test_summary_spending_threshold_accepts_none_zero_and_positive(
    value: Decimal | None,
) -> None:
    assert _plan_with(value).summary_spending_threshold == value


def test_summary_spending_threshold_rejects_negative() -> None:
    with pytest.raises(ValidationError):
        _plan_with(Decimal("-1"))


def test_summary_spending_threshold_persists_through_repository(
    repo: PlanRepository,
) -> None:
    plan_id, plan = repo.create(name="Threshold plan")
    updated = plan.model_copy(update={"summary_spending_threshold": Decimal("12000")})
    repo.save(plan_id, updated)

    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    assert loaded.summary_spending_threshold == Decimal("12000")
