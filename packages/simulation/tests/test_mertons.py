import math

import pytest
from simulation.mertons import (
    effective_mertons,
    get_rra_for_all_stocks,
    plain_mertons,
)

TOL = 1e-9


# Each case: (annual_stock, annual_bond, variance, rra, time_pref, add_tilt,
#             expected_stock_allocation, expected_monthly_spending_tilt)
# pinned: tpaw mertons_formula.cu plain_mertons_formula TEST_CASE
PLAIN_CASES = [
    # RRA=4
    (0.05, 0.03, 0.01, 4.0, 0.01, 0.0, 0.5000000000000001, 0.0009327004773649339),
    # RRA=0.04, Very low RRA → >100% raw equity allocation (50×)
    (0.05, 0.03, 0.01, 0.04, 0.01, 0.0, 50.00000000000001, 0.24962776727305425),
    # Infinite RRA → 0% stocks
    (0.05, 0.03, 0.01, math.inf, 0.01, 0.0, 0.0, 0.0),
    # Zero equity premium → 0% stocks
    (0.03, 0.03, 0.01, 4.0, 0.01, 0.0, 0.0, 0.00041571484472902043),
    # Negative time preference
    (0.05, 0.03, 0.01, 4.0, -0.1, 0.0, 0.5000000000000001, 0.003173196227570285),
    # additional spending tilt
    (0.05, 0.03, 0.01, 4.0, 0.01, 1.0, 0.5000000000000001, 0.059958441910258564),
    # effective floor for RRA (most aggressive equity allocation Merton allows without leverage)
    (0.05, 0.03, 0.01, 2.0000000000000004, 0.01, 0.0, 1.0, 0.002059836269842741),
]


@pytest.mark.parametrize("stock,bond,var,rra,tp,tilt,exp_alloc,exp_tilt", PLAIN_CASES)
def test_plain_mertons_matches_tpaw(
    stock, bond, var, rra, tp, tilt, exp_alloc, exp_tilt
):
    result = plain_mertons(
        annual_bond_return=bond,
        annual_equity_premium=stock - bond,
        annual_variance_stocks=var,
        rra=rra,
        time_preference=tp,
        annual_additional_spending_tilt=tilt,
    )

    assert result.stock_allocation == pytest.approx(exp_alloc, abs=TOL)
    assert result.spending_tilt == pytest.approx(exp_tilt, abs=TOL)


# pinned: tpaw mertons_formula.cu effective_mertons_formula TEST_CASE
EFFECTIVE_CASES = [
    # passthru
    (0.05, 0.03, 0.01, 4.0, 0.01, 0.0, 0.5000000000000001, 0.0009327004773649339),
    # effective floor for rra
    (0.05, 0.03, 0.01, 2.0000000000000004, 0.01, 0.0, 1.0, 0.002059836269842741),
    # below the effective floor
    (0.05, 0.03, 0.01, 0.05, 0.01, 0.0, 1.0, 0.002059836269842741),
    # neg equity premium
    (0.02, 0.03, 0.01, 4.0, 0.01, 0.0, 0.0, 0.00041571484472902043),
]


@pytest.mark.parametrize(
    "stock,bond,var,rra,tp,tilt,exp_alloc,exp_tilt", EFFECTIVE_CASES
)
def test_effective_mertons_matches_tpaw(
    stock, bond, var, rra, tp, tilt, exp_alloc, exp_tilt
):
    result = effective_mertons(
        annual_bond_return=bond,
        annual_equity_premium=stock - bond,
        annual_variance_stocks=var,
        rra=rra,
        time_preference=tp,
        annual_additional_spending_tilt=tilt,
    )

    assert result.stock_allocation == pytest.approx(exp_alloc, abs=TOL)
    assert result.spending_tilt == pytest.approx(exp_tilt, abs=TOL)


def test_get_rra_for_all_stocks():
    # pinned: tpaw mertons_formula.cu _get_rra_for_all_stocks TEST_CASE
    annual_stock = 0.05
    annual_bond = 0.03
    variance = 0.01
    equity_premium = annual_stock - annual_bond
    expected_rra_typical = 2.0000000000000004  # pinned contract value from tpaw doctest
    expected_rra_zero_premium = 0.0

    assert get_rra_for_all_stocks(equity_premium, variance) == pytest.approx(
        expected_rra_typical, abs=TOL
    )
    assert get_rra_for_all_stocks(annual_bond - annual_bond, variance) == pytest.approx(
        expected_rra_zero_premium, abs=TOL
    )
