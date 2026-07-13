from datetime import date
from decimal import Decimal

import numpy as np
import pytest
from core.defaults import default_plan
from core.models import PersonHousehold
from simulation.preprocess import ProcessedPlan, preprocess
from simulation.risk import rra_by_month


def test_preprocess_shapes_and_basic_invariants():
    plan = default_plan()
    today = date(2026, 1, 1)

    processed = preprocess(plan, today=today)

    months = processed.months
    assert isinstance(processed, ProcessedPlan)
    assert processed.income_real.shape == (months,)
    assert processed.essential_real.shape == (months,)
    assert processed.discretionary_real.shape == (months,)
    assert processed.stock_allocation_total_portfolio.shape == (months,)
    assert processed.spending_tilt.shape == (months,)
    assert processed.cumulative_1_plus_g_over_1_plus_r.shape == (months,)
    # Allocation is a fraction in [0, 1].
    assert np.all(processed.stock_allocation_total_portfolio >= 0.0)
    assert np.all(processed.stock_allocation_total_portfolio <= 1.0)
    assert processed.gross_job.shape == (months,)
    assert processed.gross_social_security.shape == (months,)
    assert processed.gross_pension.shape == (months,)
    assert processed.gross_manual.shape == (months,)
    assert processed.taxes.shape == (months,)


def test_legacy_npv_zero_when_no_legacy_target():
    plan = default_plan()
    expected_legacy_target = Decimal(0)
    plan.legacy_target = expected_legacy_target
    today = date(2026, 1, 1)

    processed = preprocess(plan, today=today)

    assert np.allclose(processed.legacy_npv, 0.0)


def test_age_glide_rra_tracks_person_with_latest_end_date_not_highest_max_age():
    # Regression guard: the age-glide RRA must be driven by whichever person's
    # plan ends *latest in absolute calendar time* (matching
    # core.timeline.horizon_months's own criterion: birth_year + max_age_years),
    # not by whoever has the numerically larger max_age_years. person1 here has
    # the higher max_age_years but an earlier absolute end date (born earlier);
    # person2 has the lower max_age_years but ends later and therefore defines
    # both the simulation horizon and the age-glide reference.
    plan = default_plan()
    plan.household.person1 = PersonHousehold(
        birth_month=1, birth_year=1960, max_age_years=90
    )
    plan.household.person2 = PersonHousehold(
        birth_month=1, birth_year=1990, max_age_years=85
    )
    plan.risk.delta_at_max_age = Decimal(-10)
    today = date(2026, 1, 1)
    person2 = plan.household.person2
    person2_current_age_months = (today.year - person2.birth_year) * 12 + (
        today.month - person2.birth_month
    )
    person2_max_age_months = person2.max_age_years * 12

    processed = preprocess(plan, today=today)

    expected_rra = rra_by_month(
        plan.risk,
        num_months=processed.months,
        current_age_months=person2_current_age_months,
        max_age_months=person2_max_age_months,
    )
    assert np.allclose(processed.rra, expected_rra)


def test_cashflow_horizon_mismatch_raises_value_error(monkeypatch):
    import sys

    # `simulation/__init__.py` re-exports the `preprocess` function under the
    # same name as this submodule, shadowing `simulation.preprocess` as a
    # package attribute — so fetch the real module via sys.modules instead of
    # `import simulation.preprocess as ...`.
    preprocess_module = sys.modules["simulation.preprocess"]

    plan = default_plan()
    today = date(2026, 1, 1)

    class _MismatchedCashflows:
        net_cashflow = [0.0]  # deliberately shorter than the real horizon

    monkeypatch.setattr(
        preprocess_module,
        "build_monthly_cashflows",
        lambda plan, *, today: _MismatchedCashflows(),
    )

    with pytest.raises(ValueError, match="horizon"):
        preprocess(plan, today=today)


def test_negative_planning_bond_return_raises_value_error():
    invalid_return = Decimal("-1.5")
    plan = default_plan()
    plan.planning_returns.preset = "fixed"
    plan.planning_returns.expected_annual_return_bonds = invalid_return
    today = date(2026, 1, 1)

    with pytest.raises(ValueError, match="bond"):
        preprocess(plan, today=today)


def test_negative_planning_stock_return_raises_value_error():
    invalid_return = Decimal("-1.5")
    plan = default_plan()
    plan.planning_returns.preset = "fixed"
    plan.planning_returns.expected_annual_return_stocks = invalid_return
    today = date(2026, 1, 1)

    with pytest.raises(ValueError, match="stock"):
        preprocess(plan, today=today)
