from datetime import date
from decimal import Decimal

import numpy as np
from core.defaults import default_plan
from simulation.preprocess import ProcessedPlan, preprocess


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


def test_legacy_npv_zero_when_no_legacy_target():
    plan = default_plan()
    expected_legacy_target = Decimal(0)
    plan.legacy_target = expected_legacy_target
    today = date(2026, 1, 1)

    processed = preprocess(plan, today=today)

    assert np.allclose(processed.legacy_npv, 0.0)
