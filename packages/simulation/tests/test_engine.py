import numpy as np
import pytest
from simulation.engine import simulate_monthly
from simulation.preprocess import ProcessedPlan


def _flat_processed(
    months: int,
    *,
    starting_balance: float,
    essential_real: np.ndarray | None = None,
) -> ProcessedPlan:
    zeros = np.zeros(months, dtype=np.float64)
    return ProcessedPlan(
        months=months,
        starting_balance=starting_balance,
        income_real=zeros.copy(),
        essential_real=zeros.copy() if essential_real is None else essential_real,
        discretionary_real=zeros.copy(),
        rra=np.full(months, 4.0),
        stock_allocation_total_portfolio=np.full(months, 0.5),
        legacy_stock_allocation=0.5,
        spending_tilt=zeros.copy(),
        npv_income_without_current=zeros.copy(),
        npv_essential_without_current=zeros.copy(),
        npv_discretionary_without_current=zeros.copy(),
        legacy_npv=zeros.copy(),
        cumulative_1_plus_g_over_1_plus_r=np.arange(months, 0, -1, dtype=np.float64),
        monthly_planning_stocks=0.0,
        monthly_planning_bonds=0.0,
    )


def test_zero_return_zero_income_spends_down_general_pool():
    months = 3
    starting_balance = 300.0
    processed = _flat_processed(months, starting_balance=starting_balance)
    # cumulative = [3, 2, 1]; with zero returns the general pool amortizes evenly.
    returns_stocks = np.zeros((1, months), dtype=np.float64)
    returns_bonds = np.zeros((1, months), dtype=np.float64)

    result = simulate_monthly(
        processed, stocks_return=returns_stocks, bonds_return=returns_bonds
    )

    expected_monthly_withdrawal = starting_balance / months
    assert result.withdrawals_general[0, 0] == pytest.approx(
        expected_monthly_withdrawal
    )
    assert result.withdrawals_general[0, 1] == pytest.approx(
        expected_monthly_withdrawal
    )
    assert result.withdrawals_general[0, 2] == pytest.approx(
        expected_monthly_withdrawal
    )
    assert result.balance_start[0, 0] == pytest.approx(starting_balance)


def test_money_is_conserved_with_zero_returns():
    months = 4
    starting_balance = 1000.0
    processed = _flat_processed(months, starting_balance=starting_balance)
    z = np.zeros((1, months), dtype=np.float64)

    result = simulate_monthly(processed, stocks_return=z, bonds_return=z.copy())

    # With zero income and zero returns, total withdrawals cannot exceed starting balance.
    assert result.withdrawals_total.sum() <= starting_balance + 1e-6


def test_current_month_essential_is_reserved_before_general_pool():
    # Regression guard: the wealth-based pool carve must reserve the *current*
    # month's essential expense (npv_essential_without_current + current), not
    # just the future NPV. Otherwise the general pool — and therefore the first
    # general withdrawal target — is overstated. With a single future-free
    # essential expense at month 0 and zero returns, the general pool is
    # (balance - essential) and month 0 amortizes it over `cumulative[0]`.
    months = 2
    starting_balance = 1000.0
    current_essential = 200.0
    essential_real = np.array([current_essential, 0.0], dtype=np.float64)
    processed = _flat_processed(
        months, starting_balance=starting_balance, essential_real=essential_real
    )
    # cumulative = [2, 1]; no future essential NPV, zero income, zero returns.
    z = np.zeros((1, months), dtype=np.float64)

    result = simulate_monthly(processed, stocks_return=z, bonds_return=z.copy())

    cumulative_month_0 = processed.cumulative_1_plus_g_over_1_plus_r[0]
    expected_general_month_0 = (
        starting_balance - current_essential
    ) / cumulative_month_0
    assert result.withdrawals_essential[0, 0] == pytest.approx(current_essential)
    assert result.withdrawals_general[0, 0] == pytest.approx(expected_general_month_0)
    # Nothing is left unaccounted: essential + both general draws == starting balance.
    assert result.withdrawals_total.sum() == pytest.approx(starting_balance)
