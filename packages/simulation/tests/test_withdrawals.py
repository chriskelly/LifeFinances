import pytest
from simulation.withdrawals import (
    apply_allocation,
    apply_contributions_and_withdrawals,
)

TOL = 1e-9


def test_contributions_and_withdrawals_sufficient():
    # pinned: tpaw run_common.cu apply_contributions_and_withdrawals sufficient_funds
    balance_starting = 10000.0
    contributions = 1000.0
    essential = 1000.0
    discretionary = 2000.0
    general = 3000.0

    result = apply_contributions_and_withdrawals(
        balance_starting=balance_starting,
        contributions=contributions,
        essential=essential,
        discretionary=discretionary,
        general=general,
    )

    expected_total = essential + discretionary + general
    assert result.essential == pytest.approx(essential, abs=TOL)
    assert result.discretionary == pytest.approx(discretionary, abs=TOL)
    assert result.general == pytest.approx(general, abs=TOL)
    assert result.total == pytest.approx(expected_total, abs=TOL)
    assert result.from_savings_rate == pytest.approx(
        (expected_total - contributions) / balance_starting, abs=TOL
    )
    assert result.balance == pytest.approx(
        balance_starting + contributions - expected_total, abs=TOL
    )
    assert result.insufficient is False


def test_contributions_and_withdrawals_insufficient():
    # pinned: tpaw run_common.cu apply_contributions_and_withdrawals insufficient_funds
    balance_starting = 3000.0
    contributions = 1000.0
    essential = 1000.0
    discretionary = 2000.0
    general = 3000.0

    result = apply_contributions_and_withdrawals(
        balance_starting=balance_starting,
        contributions=contributions,
        essential=essential,
        discretionary=discretionary,
        general=general,
    )

    expected_general = 1000.0  # pinned: clamped after essential + discretionary
    expected_total = essential + discretionary + expected_general

    assert result.general == pytest.approx(expected_general, abs=TOL)
    assert result.total == pytest.approx(expected_total, abs=TOL)
    assert result.from_savings_rate == pytest.approx(
        (expected_total - contributions) / balance_starting, abs=TOL
    )
    assert result.balance == pytest.approx(0.0, abs=TOL)
    assert result.insufficient is True


def test_apply_allocation_basic():
    # pinned: tpaw run_common.cu apply_allocation basic
    stock_allocation = 0.5
    stock_return = 0.05
    bond_return = 0.03
    balance = 1000.0
    npv_income = 100.0

    result = apply_allocation(
        stock_allocation=stock_allocation,
        stock_return=stock_return,
        bond_return=bond_return,
        balance=balance,
        npv_income_without_current_month=npv_income,
    )

    stocks_amount = balance * stock_allocation
    bonds_amount = balance - stocks_amount
    expected_balance = stocks_amount * (1.0 + stock_return) + bonds_amount * (
        1.0 + bond_return
    )
    total_portfolio = balance + npv_income

    assert result.balance == pytest.approx(expected_balance, abs=TOL)
    assert result.stock_allocation_on_total == pytest.approx(
        stocks_amount / total_portfolio, abs=TOL
    )
